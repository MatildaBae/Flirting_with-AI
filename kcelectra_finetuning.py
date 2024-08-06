# -*- coding: utf-8 -*-
"""KcELECTRA_Finetuning_0701.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/19IF4qE50C3L5z_vdc0qyteEjMx8NHk-8

참고: https://github.com/searle-j/KOTE/blob/main/codes/KOTE_pytorch_lightning.ipynb
"""

from google.colab import drive
drive.mount('/content/drive')

!pip install pytorch_lightning
!pip install datasets

import numpy as np
import pandas as pd

from tqdm.notebook import tqdm

import torch ## version >= 1.8.2
import torch.nn as nn

import pytorch_lightning as pl ## version == 1.4.9

import datasets ## version == 2.1.0

from transformers import AutoTokenizer, AutoModel ## version == 4.12.3

data = pd.read_csv('/content/drive/MyDrive/abba_emotion_label.csv')
data

# Convert the 'encoded_labels' column from string to list of integers
data['encoded_labels'] = data['encoded_labels'].apply(lambda x: eval(x))

"""### Data"""

from datasets import Dataset, DatasetDict

df = pd.DataFrame(data)
df = df[['Unnamed: 0', 'combined', 'encoded_labels']]

# 칼럼명 변경
df = df.rename(columns={"Unnamed: 0": "ID", "combined": "text", "encoded_labels": "labels"})
# df['ID'] = df['ID'].to_string()

# 데이터 분할
train_df = df.sample(n=40000)
test_df = df.sample(n=5000)
validation_df = df.sample(n=5000, replace=True, random_state=42)

train_df

# Dataset으로 변환
train_dataset = Dataset.from_pandas(train_df)
test_dataset = Dataset.from_pandas(test_df)
validation_dataset = Dataset.from_pandas(validation_df)

# DatasetDict 생성
dataset = DatasetDict({
    "train": train_dataset,
    "test": test_dataset,
    "validation": validation_dataset
})

dataset

## convert the integer labels into multi-hot form (44-dimensional).

from sklearn.preprocessing import MultiLabelBinarizer

mlb = MultiLabelBinarizer()
train_labels = mlb.fit_transform(dataset["train"]["labels"])
test_labels = mlb.fit_transform(dataset["test"]["labels"])
val_labels = mlb.fit_transform(dataset["validation"]["labels"])

print("train_labels shape ::: {}".format(train_labels.shape))
print("test_labels shape :::: {}".format(test_labels.shape))
print("val_labels shape ::::: {}".format(val_labels.shape))
print("\ncool..!!")

## check one sample in the train set.

# dataset["train"][25597]

## extract the texts, since we will use a custom datset not the huggingface dataset.

train_texts = dataset["train"]["text"]
test_texts = dataset["test"]["text"]
val_texts = dataset["validation"]["text"]

LABELS = ['불평/불만',
 '환영/호의',
 '감동/감탄',
 '지긋지긋',
 '고마움',
 '슬픔',
 '화남/분노',
 '존경',
 '기대감',
 '우쭐댐/무시함',
 '안타까움/실망',
 '비장함',
 '의심/불신',
 '뿌듯함',
 '편안/쾌적',
 '신기함/관심',
 '아껴주는',
 '부끄러움',
 '공포/무서움',
 '절망',
 '한심함',
 '역겨움/징그러움',
 '짜증',
 '어이없음',
 '없음',
 '패배/자기혐오',
 '귀찮음',
 '힘듦/지침',
 '즐거움/신남',
 '깨달음',
 '죄책감',
 '증오/혐오',
 '흐뭇함(귀여움/예쁨)',
 '당황/난처',
 '경악',
 '부담/안_내킴',
 '서러움',
 '재미없음',
 '불쌍함/연민',
 '놀람',
 '행복',
 '불안/걱정',
 '기쁨',
 '안심/신뢰']

"""### tokenization"""

## download the pretrained tokenizer from huggingface.

MODEL_NAME = "beomi/KcELECTRA-base" # <-- Thank you!
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def token_masking(encoding, prob):
    for i, token in enumerate(encoding["input_ids"][0]):
        if token not in [0,1,2,3]: # 0 ~ 3, [PAD], [UNK], [CLS], and [SEP], respectively.
            if np.random.uniform(0,1) < prob:
                encoding["input_ids"][0][i] = 4 # 4 is [MASK]

    return encoding

def token_switching(encoding, prob):
    for i, token in enumerate(encoding["input_ids"][0]):
        if token not in [0,1,2,3,4]: # 0 ~ 4, [PAD], [UNK], [CLS], [SEP], and [MASK], respectively.
            if np.random.uniform(0,1) < prob:
                encoding["input_ids"][0][i] = np.random.choice(np.arange(5,tokenizer.vocab_size), 1)[0]

    return encoding

def mask_and_switch(encoding, prob=0.1):
    encoding = token_masking(encoding, prob/2)
    encoding = token_switching(encoding, prob/2)

    return encoding

"""### custom dataset"""

from torch.utils.data import Dataset

## maximum token lengths

MAX_LENGTH = 512

## define our dataset...!

class KOTEDataset(Dataset):

    def __init__(self, texts, labels, tokenizer, max_length:int=MAX_LENGTH,
                would_you_like_some_mask_and_switch:bool=False):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.mask = would_you_like_some_mask_and_switch

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx:int):
        text = self.texts[idx]
        labels = self.labels[idx]
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
            return_token_type_ids=False,
        )

        if self.mask:
            encoding = mask_and_switch(encoding, prob=0.1)
        else:
            pass

        return dict(
          input_ids=encoding["input_ids"].flatten(),
          attention_mask=encoding["attention_mask"].flatten(),
          labels=torch.FloatTensor(labels), ## must be a float tensor.
        )

## create the datasets.

train_dataset = KOTEDataset(train_texts, train_labels, tokenizer=tokenizer, would_you_like_some_mask_and_switch=True)
test_dataset = KOTEDataset(test_texts, test_labels, tokenizer=tokenizer)
val_dataset = KOTEDataset(val_texts, val_labels, tokenizer=tokenizer)

"""### modeling"""

## download the pretrained electra model.

electra = AutoModel.from_pretrained(MODEL_NAME, return_dict=True)

## we will use the default arguments, except for the last gelu for classification.

electra.config

"""### dataloader with pl"""

from torch.utils.data import DataLoader

class KOTEDataModule(pl.LightningDataModule):

    def __init__(self, train_dataset, test_dataset, val_dataset, batch_size=32):
        super().__init__()
        self.batch_size = batch_size
        self.train_dataset = train_dataset
        self.test_dataset = test_dataset
        self.val_dataset = val_dataset

    def train_dataloader(self):
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=6, ## choose a befitting number depending on your environment.
        )
    def val_dataloader(self):
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            num_workers=6, ## choose a befitting number depending on your environment.
        )
    def test_dataloader(self):
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            num_workers=6, ## choose a befitting number depending on your environment.
        )

BATCH_SIZE = 16 ## about 28 ~ 30 Gb memory required, if my memory serves me right.

data_module = KOTEDataModule(
  train_dataset,
  test_dataset,
  val_dataset,
  batch_size=BATCH_SIZE,
)

"""### model"""

from transformers import AdamW, get_linear_schedule_with_warmup

INITIAL_LR = 2e-5

import torch
import torch.nn as nn
from transformers import AdamW, get_linear_schedule_with_warmup
import pytorch_lightning as pl

class KOTETagger(pl.LightningModule):

    def __init__(self, electra, n_training_steps=None, n_warmup_steps=None, gamma_for_expLR=None):
        super().__init__()
        self.electra = electra
        self.classifier = nn.Linear(self.electra.config.hidden_size, 44)
        self.n_training_steps = n_training_steps
        self.n_warmup_steps = n_warmup_steps

        # the loss
        self.criterion = nn.BCELoss()

        # storage for epoch end
        self.training_step_outputs = []
        self.validation_step_outputs = []

    def forward(self, input_ids, attention_mask, labels=None):
        output = self.electra(input_ids, attention_mask=attention_mask)
        output = output.last_hidden_state[:,0,:]  # [CLS] of the last hidden state
        output = self.classifier(output)
        output = torch.sigmoid(output)
        loss = 0
        if labels is not None:
            loss = self.criterion(output, labels)

        torch.cuda.empty_cache()

        return loss, output

    def step(self, batch, batch_idx):
        input_ids = batch["input_ids"]
        attention_mask = batch["attention_mask"]
        labels = batch["labels"]
        loss, outputs = self.forward(input_ids, attention_mask, labels)

        preds = outputs

        y_true = list(labels.detach().cpu())
        y_pred = list(preds.detach().cpu())

        return {"loss": loss, "y_true": y_true, "y_pred": y_pred}

    def training_step(self, batch, batch_idx):
        output = self.step(batch, batch_idx)
        self.training_step_outputs.append(output["loss"])
        # torch.cuda.empty_cache()  # Clear the cache
        return output

    def validation_step(self, batch, batch_idx):
        output = self.step(batch, batch_idx)
        self.validation_step_outputs.append(output["loss"])
        return output

    def on_epoch_end(self, outputs, state="train"):
        loss = torch.tensor(0, dtype=torch.float)
        for out in outputs:
            loss += out.detach().cpu()
        loss = loss / len(outputs)

        self.log(state + "_loss", float(loss), on_epoch=True, prog_bar=True)
        print(f"[Epoch {self.trainer.current_epoch} {state.upper()}] Loss: {loss}")
        return {"loss": loss}

    def on_train_epoch_end(self):
        self.on_epoch_end(self.training_step_outputs, state="train")
        self.training_step_outputs.clear()  # free memory

    def on_validation_epoch_end(self):
        self.on_epoch_end(self.validation_step_outputs, state="val")
        self.validation_step_outputs.clear()  # free memory

    def configure_optimizers(self):
        optimizer = AdamW(self.parameters(), lr=INITIAL_LR)

        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=self.n_warmup_steps,
            num_training_steps=self.n_training_steps
        )

        return dict(
          optimizer=optimizer,
          lr_scheduler=dict(
            scheduler=scheduler,
            interval="step"
          )
        )

## determine the schedule for our optimizer

N_EPOCHS = 10

steps_per_epoch = len(train_dataset) // BATCH_SIZE
TOTAL_STEPS = steps_per_epoch * N_EPOCHS
WARMUP_STEPS = TOTAL_STEPS // 5
WARMUP_STEPS, TOTAL_STEPS

## define the model.

model = KOTETagger(
    electra=electra,
    n_warmup_steps=WARMUP_STEPS,
    n_training_steps=TOTAL_STEPS,
)

"""### training"""

## set a logger and some stuffs...

from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
from pytorch_lightning.loggers import TensorBoardLogger

## the check point
checkpoint_callback = ModelCheckpoint(
    dirpath="/content/drive/MyDrive",
    filename="epoch{epoch}-val_loss{val_loss:.4f}",
    monitor="val_loss",
    save_top_k=1,
    mode="min",
    auto_insert_metric_name=False,
    every_n_epochs=1  # <-- Added to save at every epoch
)

## for early stopping
early_stopping_callback = EarlyStopping(monitor="val_loss", patience=5, min_delta=0.00)

## the logger
logger = TensorBoardLogger("/content/sample_data", name="/content/sample_data")

## trainer

N_EPOCHS = 15 ## redefine the number of the epochs, just to make sure there is no more room to improve.

trainer = pl.Trainer(
    logger=logger,
    callbacks=[checkpoint_callback, early_stopping_callback],
    max_epochs=N_EPOCHS,
    accelerator='gpu',    # Use 'gpu' accelerator
    devices=1,          # GPU number
    enable_progress_bar=True,  # Enable progress bar
    # progress_bar_refresh_rate=5 # (optional) refresh rate for the progress bar
)

## about 4 ~ 5 hours to reach the optimum...

trainer.fit(model, data_module)

"""### prediction"""

from glob import glob

par_dir = './YOUR_FOLDER_NAME/ONE_MORE_FOLDER_NAME/version_0/checkpoints/'
best_ckpt = sorted(glob(par_dir + '*.ckpt'))[-1]
best_ckpt

best_ckpt = '/content/drive/MyDrive/epoch4-val_loss0.1180.ckpt'

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
device

gruesome_mind_reader = KOTETagger.load_from_checkpoint(best_ckpt, electra=electra)

gruesome_mind_reader.eval()
gruesome_mind_reader.freeze()

# 텍스트 데이터 토큰화 및 텐서로 변환 함수
def tokenize_and_tensorize(texts, tokenizer, device):
    encodings = tokenizer(list(texts), padding=True, truncation=True, return_tensors='pt')
    input_ids = encodings['input_ids'].to(device)
    attention_mask = encodings['attention_mask'].to(device)
    return input_ids, attention_mask

# 텍스트 데이터 텐서로 변환 및 GPU로 이동
train_input_ids, train_attention_mask = tokenize_and_tensorize(train_texts, tokenizer, device)
test_input_ids, test_attention_mask = tokenize_and_tensorize(test_texts, tokenizer, device)
val_input_ids, val_attention_mask = tokenize_and_tensorize(val_texts, tokenizer, device)

# 레이블을 텐서로 변환 및 GPU로 이동
train_labels_tensor = torch.tensor(train_labels).to(device)
test_labels_tensor = torch.tensor(test_labels).to(device)
val_labels_tensor = torch.tensor(val_labels).to(device)

# 예측 수행 함수
def predict(texts, tokenizer, model, device, threshold=0.3):
    encoding = tokenizer(texts, padding=True, truncation=True, return_tensors='pt')
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    with torch.no_grad():
        _, predictions = model(input_ids, attention_mask)
    predictions = predictions.flatten().cpu().numpy()

    for l, p in zip(LABELS, predictions):
        if p < threshold:
            continue
        print(f"{l}: {p}")

# 예측 수행
sample_texts = ["안녕 반가워!"]
for text in sample_texts:
    print(f"Text: {text}")
    predict(text, tokenizer, gruesome_mind_reader, device)
    print("\n")

"""### evaluation"""

predictions = []
labels = []

for item in tqdm(test_dataset):
    _, pred = gruesome_mind_reader(
        item["input_ids"].unsqueeze(dim=0).to(device),
        item["attention_mask"].unsqueeze(dim=0).to(device)
        )
    predictions.append(pred.flatten())
    labels.append(item["labels"].round().int())

predictions = torch.stack(predictions).detach().cpu()
labels = torch.stack(labels).detach().cpu()

# !pip install torchmetrics

import torch
from torchmetrics.functional import accuracy, f1_score, auroc

# 임계값 설정
THRESHOLD = 0.3

# 예측값 이진화 (임계값 적용)
binary_predictions = (predictions >= THRESHOLD).int()

# 정확도 계산
acc = accuracy(binary_predictions, labels.int(), task="binary")
print(f"Accuracy: {acc}")

# F1 점수 계산
f1 = f1_score(binary_predictions, labels.int(), task="binary")
print(f"F1 Score: {f1}")

# AUROC 계산
auc = auroc(predictions, labels.int(), task="binary")
print(f"AUROC: {auc}")

## we should check the roc scores, since KOTE is imbalanced..!
## 안 됨 !!!


macro_auroc = []
print("AUROC per tag")
for i, name in enumerate(LABELS):
    try:
        tag_auroc = auroc(predictions[:, i], labels[:, i], pos_label=1)
        macro_auroc.append(tag_auroc)
        print(f"{i}:: {str(name)}: {tag_auroc}")
    except:
        pass

print()
print("MACRO_AVG :: {}".format(np.array(macro_auroc).mean()))

from sklearn.metrics import classification_report, multilabel_confusion_matrix
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

y_pred = predictions.numpy()
y_true = labels.numpy()
upper, lower = 1, 0
y_pred = np.where(y_pred > THRESHOLD, upper, lower)
print(classification_report(
  y_true,
  y_pred,
  target_names=LABELS,
  zero_division=0
))

## computation of some vector is impossible if it is a zero vector with zero variance. --> just turn off error signs

from sklearn.metrics import matthews_corrcoef as MCC
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("error")

    totalCorr = 0
    totalLen = 0
    for i in range(10_000):
        try:
            totalCorr += MCC(y_pred[i], y_true[i])
            totalLen += 1
        except:
            pass

print('computed # ::: {}'.format(totalLen))
print('MCC  :::::::::  {}'.format(totalCorr/totalLen))

