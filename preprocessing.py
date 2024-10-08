# -*- coding: utf-8 -*-
"""Preprocessing

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1sYqp92AoL9nmL-LvxuYco2V2jzpMjS1i
"""

from google.colab import drive
drive.mount('/content/drive')

import numpy as np
import pandas as pd

input = pd.read_csv('/content/drive/MyDrive/24-1-nlp/chatbot/inputforchatbottrain.csv',index_col=0)

"""## 전처리 <- 이거!"""

!pip install soynlp

# 패키지 불러오기

import numpy as np
import pandas as pd
import re
import requests
from soynlp.normalizer import *

raw = pd.read_csv('/content/drive/MyDrive/24-1-nlp/chat_rawdata/train_filtered2.csv')

# 원본 데이터의 사본 생성
new = raw.copy()
new

# 시스템 문구 삭제 함수
def remove_system_phrases(text):
    system_phrases = [
        r'#@시스템#동영상#', r'#@시스템#사진#', r'#@이모티콘#', r'#@기타#', r'#@시스템#기타#'
    ]
    for phrase in system_phrases:
        text = re.sub(phrase, '', text)
    return text

# 이모티콘 삭제 함수
def remove_emoticons(text):
    emoticon_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # 이모티콘
        u"\U0001F300-\U0001F5FF"  # 기호 & 픽토그램
        u"\U0001F680-\U0001F6FF"  # 교통 & 지도 기호
        u"\U0001F1E0-\U0001F1FF"  # 깃발 (iOS)
        u"\U00002700-\U000027BF"  # 기타 기호
        u"\U0001F900-\U0001F9FF"  # 추가 기호
        "]+", flags=re.UNICODE)
    return emoticon_pattern.sub(r'', text)

# 인명 가명, 주소 처리 함수
def replace_names(text):
    text = re.sub(r'#@이름#', '<이름>', text)
    text = re.sub(r'#@주소#', '<주소>', text)
    return text

# 초성 처리 함수
def handle_consonants(text):
    # 초성이 4개 이상 반복되는 경우 4개까지만 남기기
    text = repeat_normalize(text, num_repeats=4)

    # 1~3개 반복되는 초성이 초성이 아닌 것들 사이에 있을 때 삭제
    text = re.sub(r'([^ㄱ-ㅎ]|^)([ㄱ-ㅎ]{1,3})([^ㄱ-ㅎ]|$)', r'\1\3', text)

    return text

# 전체 전처리 함수
def preprocess_text(text):
    text = remove_system_phrases(text)
    text = remove_emoticons(text)
    text = replace_names(text)
    text = handle_consonants(text)
    # text = correct_typos(text)
    return text

# 데이터셋 사본에 전처리 적용
new['utterance'] = new['utterance'].apply(preprocess_text)
new[0:50]

# 변경된 부분 확인
changed = new[new['utterance'] != raw['utterance']].copy()
changed['original'] = raw['utterance']
changed['processed'] = new['utterance']

# 변경된 부분만 포함하도록 데이터프레임 축소
changed = changed[['original', 'processed']]
changed

# 결측치 확인
# 'utterance' 컬럼에서 빈 문자열 개수 세기
empty_strings = new['utterance'] == ''
empty_count = empty_strings.sum()

print("빈 문자열의 개수:", empty_count)

# 'utterance' 열에서 빈 문자열을 가진 행의 'dialogueID2' 값 찾기
empty_scenario_ids = new[new['utterance'] == '']['dialogueID2'].unique()

# 해당 'dialogueID2'를 가진 모든 행을 제거
new_cleaned = new[~new['dialogueID2'].isin(empty_scenario_ids)]

# 제거된 행의 개수를 출력합니다.
print(f"총 제거된 행 개수: {len(new) - len(new_cleaned)}")

new_cleaned.reset_index(drop=True, inplace=True)

new_cleaned[0:50]

new_cleaned.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed0610.csv')

new_cleaned500 = new_cleaned[0:500][['dialogueID2', 'utterance']]
new_cleaned_utterance = new_cleaned[['dialogueID2', 'utterance']]

print(new_cleaned500)

# new_cleaned500.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed_utterance0604_500.csv')
new_cleaned500.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed_utterance0610_500.csv')

new_cleaned_utterance.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed_utterance0610.csv')

new.to_csv('/content/drive/MyDrive/24-1-nlp/chat_rawdata/preprocessedsample_500')

"""## 채팅 데이터 제작을 위해 dialogueID2, participantID, utterance로 구성된 df 제작"""

cleaned = pd.read_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed0610.csv')

cleaned.head()

preprocessed_speaker = cleaned[['dialogueID2','participantID','utterance']]

preprocessed_speaker500 = preprocessed_speaker[0:500]

# preprocessed_speaker500.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed0610_500_participant.csv')
preprocessed_speaker.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed0610_participant.csv')

"""## 숨김

"""

!pip install git+https://github.com/ssut/py-hanspell.git

# Commented out IPython magic to ensure Python compatibility.
!git clone https://github.com/ssut/py-hanspell.git
# %cd py-hanspell
!python setup.py install

# Commented out IPython magic to ensure Python compatibility.
# 이미 clone된 py-hanspell 폴더로 이동
# %cd py-hanspell

# 4eb98863c916079977dddc5383d0923590246289 passportKey를 spell_checker.py 파일에 적용
def fix_spell_checker_py_code(file_path, passportKey):
    pattern = r"'passportKey': '.*'"
    with open(file_path, 'r', encoding='utf-8') as input_file:
        content = input_file.read()
        modified_content = re.sub(pattern, f"'passportKey': '{passportKey}'", content)
    with open(file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(modified_content)
    return

# spell_checker.py 파일 경로
spell_checker_file_path = '/content/py-hanspell/hanspell/spell_checker.py'

# passportKey 적용
passport_key = '4eb98863c916079977dddc5383d0923590246289'
fix_spell_checker_py_code(spell_checker_file_path, passport_key)
print("passportKey가 성공적으로 적용되었습니다.")

import re
import requests

def get_passport_key():
    """네이버에서 '네이버 맞춤법 검사기' 페이지에서 passportKey를 획득

        - 네이버에서 '네이버 맞춤법 검사기'를 띄운 후
        html에서 passportKey를 검색하면 값을 찾을 수 있다.

        - 찾은 값을 spell_checker.py 48 line에 적용한다.
    """

    url = "https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8&query=네이버+맞춤법+검사기"
    res = requests.get(url)

    html_text = res.text

    match = re.search(r'passportKey=([^&"}]+)', html_text)
    if match:
        passport_key = match.group(1)
        return passport_key
    else:
        return False


def fix_spell_checker_py_code(file_path, passportKey):
    """획득한 passportkey를 spell_checker.py파일에 적용"""

    pattern = r"'passportKey': '.*'"

    with open(file_path, 'r', encoding='utf-8') as input_file:
        content = input_file.read()
        modified_content = re.sub(pattern, f"'passportKey': '{passportKey}'", content)

    with open(file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(modified_content)

    return


# before run
spell_checker_file_path = '/content/py-hanspell/hanspell/spell_checker.py'
passport_key = get_passport_key()
if passport_key:
    fix_spell_checker_py_code(spell_checker_file_path, passport_key)
    print("passportKey가 성공적으로 적용되었습니다.")
else:
    print("passportKey를 찾을 수 없습니다.")

"""## NaN 제거(맨 처음 시도)"""

pre = pd.read_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/preprocessed0602')

pre[0:50]

# nan값 세기
pre['utterance'].isna().sum()

# unique 시나리오 개수
len(pre['dialogueID2'].unique())

nan_scenario_ids = pre[pre['utterance'].isna()]['dialogueID2'].unique()
nan_scenario_ids

# 해당 dialogueID를 가진 모든 행을 제거
pre_cleaned = pre[~pre['dialogueID2'].isin(nan_dialogue_ids)]
# 결과 저장 (원하는 파일 경로로 수정)
pre_cleaned.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/cleaned_pre_removenan.csv', index=False)

print(f"총 제거된 행 개수: {len(pre) - len(pre_cleaned)}")

# nan값 세기
pre_cleaned['utterance'].isna().sum()

# unique 시나리오 개수
len(pre_cleaned['dialogueID2'].unique())

"""## 이전 시도"""

# (기타) 비속어 리스트 로드
with open('/content/drive/MyDrive/24-1-nlp/chat_clean/badwords.txt', 'r', encoding='utf-8') as file:
    bad_words = file.read().split(',')

# 비속어 패턴 생성 함수
def create_profanity_pattern(bad_words):
    pattern = []
    for word in bad_words:
        # 공백이나 특수 문자가 포함된 경우를 처리하기 위해 각 문자 사이에 [\s\-]*를 추가
        pattern.append(''.join([char + '[\s\-]*' for char in word.strip()]))
    return '|'.join(pattern)

# 비속어 패턴 컴파일
profanity_pattern = re.compile(create_profanity_pattern(bad_words), re.IGNORECASE)

# 비속어 필터링 함수
def filter_profanity(text):
    return profanity_pattern.sub('**', text)

# 이모티콘 제거 함수
def remove_emoticons(text):
    special_char_pattern = re.compile(r'[^\w\s#@<>ㅏ-ㅣ가-힣]')  # 특수 문자 제거
    return special_char_pattern.sub('', text)

# 초성 처리 함수 -> 'ㅋㅋㅋㅋㅋㅋ' -> 'ㅋㅋㅋ' 이런 식으로 통일
def handle_consonants(text):
    preserved_patterns = [
        re.compile(r'ㅋㅋ+'),
        re.compile(r'ㅎㅎ+'),
        re.compile(r'ㅠㅠ+'),
    ]
    for pattern in preserved_patterns:
        matches = pattern.findall(text)
        for match in matches:
            text = text.replace(match, ' ' + match + ' ')
    # 초성 한 글자 제거
    text = re.sub(r'[ㄱ-ㅎ]', '', text)
    return text

# 인명 가명 처리 함수
def replace_names(text):
    return re.sub(r'#@이름#', '<김여주>', text)

# 오타 수정 함수 (예시)
# def correct_typos(text):
#     corrected_text = text  # 실제로는 Hanspell이나 Clova Studio API 사용
#     return corrected_text

# 전체 전처리 함수
def preprocess_text(text):
    text = remove_emoticons(text)
    text = handle_consonants(text)
    text = replace_names(text)
    text = filter_profanity(text)
    # text = correct_typos(text)
    return text

# 데이터셋 사본에 전처리 적용
df_copy['utternace'] = df_copy['utterance'].apply(preprocess_text)

"""3분 42초 걸림"""

# 변경된 부분 확인
changed = df_copy[df_copy['utterance'] != raw['utterance']].copy()
changed['original'] = raw['utterance']
changed['processed'] = df_copy['utterance']

changed = changed[['original', 'processed']]
changed



"""## 지피티 넣는 csv 제작"""

labeled = pd.read_csv('/content/drive/MyDrive/24-1-nlp/chat_rawdata/train200_24.csv')

labeled_simple = labeled[['utterance', 'combined_tags']]
labeled_simple

labeled_simple.to_csv('/content/drive/MyDrive/24-1-nlp/chat_rawdata/labeled22')

"""## 지피티 넣을 1~500개만"""

nan = pd.read_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/cleaned_pre_removenan.csv')

nan[450:500]

gptinput = nan[0:500]['utterance']
gptinput

gptinput.to_csv('/content/drive/MyDrive/24-1-nlp/chat_clean/gptinput500')