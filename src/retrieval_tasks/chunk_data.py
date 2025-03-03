from collections import defaultdict
from tqdm import tqdm
import os
import pandas as pd
import pickle
import logging

# from glob import glob


os.makedirs("logs", exist_ok=True)
# logging.basicConfig(
#     filename="logs/log.log",
#     level=logging.DEBUG,
#     format="[%(asctime)s | %(funcName)s @ %(pathname)s] %(message)s",
# )
logger = logging.getLogger()


class DataChunk:
    """인풋 text를 tokenizing한 뒤에 주어진 길이로 chunking 해서 반환합니다. 이때 하나의 chunk(context, index 단위)는 하나의 article에만 속해있어야 합니다."""

    def __init__(self, tokenizer, chunk_size=100, chunked_path: str = ""):
        self.chunk_size = chunk_size
        self.tokenizer = tokenizer
        self.chunked_path = chunked_path

    def chunk(self, input_file):
        """input file format은 attardi/wikiextractor에 나온 형태를 따릅니다."""
        with open(input_file, "r", encoding="utf8") as f:
            input_txt = pd.read_csv(input_file)
        chunk_list = []
        orig_text = []
        for _ , art in tqdm(input_txt.iterrows(), desc="[chunking]", total=len(input_txt)):
            title = art['title']
            text = art['content']

            encoded_title = self.tokenizer.encode(title)
            encoded_txt = self.tokenizer.encode(text)
            if len(encoded_txt) < 5:  # 본문 길이가 subword 5개 미만인 경우 패스
                logger.debug(f"title {title} has <5 subwords in its article, passing")
                continue

            # article마다 chunk_size 길이의 chunk를 만들어 list에 append. 각 chunk에는 title을 prepend합니다.
            # ref : DPR paper
            for start_idx in range(0, len(encoded_txt), self.chunk_size):
                end_idx = min(len(encoded_txt), start_idx + self.chunk_size)
                chunk = encoded_title + encoded_txt[start_idx:end_idx]
                orig_text.append(self.tokenizer.decode(chunk))
                chunk_list.append(chunk)
        return orig_text, chunk_list

    def chunk_and_save_orig_passage(
        self, input_file, chunk_size=100
    ):
        passage_path = self.chunked_path
        os.makedirs(passage_path, exist_ok=True)
        idx = 0
        orig_text, chunk_list = self.chunk(input_file)
        to_save = {idx + i: orig_text[i] for i in range(len(orig_text))}
        with open(f"{passage_path}/{idx}-{idx+len(orig_text)-1}.p", "wb") as f:
            pickle.dump(to_save, f)
        return orig_text, chunk_list

def save_orig_passage_bulk(
    input_path="text", passage_path="processed_passages", chunk_size=100
):
    """store original passages with unique id"""
    os.makedirs(passage_path, exist_ok=True)
    app = DataChunk(chunk_size=chunk_size)
    idx = 0
    for path in tqdm(glob(f"{input_path}/*/wiki_*")):
        ret, _ = app.chunk(path)
        to_save = {idx + i: ret[i] for i in range(len(ret))}
        with open(f"{passage_path}/{idx}-{idx+len(ret)-1}.p", "wb") as f:
            pickle.dump(to_save, f)
        idx += len(ret)
        # break


def save_title_index_map(
    index_path="title_passage_map.p", source_passage_path="processed_passages"
):
    """korquad와 klue 데이터 전처리를 위해 title과 passage id를 맵핑합니다.
    title_index_map : dict[str, list] 형태로, 특정 title에 해당하는 passage id를 저장합니다.
    """
    logging.getLogger()

    files = glob(f"{source_passage_path}/*")
    title_id_map = defaultdict(list)
    for f in tqdm(files):
        with open(f, "rb") as _f:
            id_passage_map = pickle.load(_f)
        for id, passage in id_passage_map.items():
            title = passage.split("[SEP]")[0].split("[CLS]")[1].strip()
            title_id_map[title].append(id)
        logger.info(f"processed {len(id_passage_map)} passages from {f}...")
    with open(index_path, "wb") as f:
        pickle.dump(title_id_map, f)
    logger.info(f"Finished saving title_index_mapping at {index_path}!")


if __name__ == "__main__":
    # 디버깅용 main
    # import argparse
    from tqdm import tqdm
    from glob import glob

    # parser = argparse.ArgumentParser()
    # parser.add_argument('--chunk_size', type=int, default=100)
    # args = parser.parse_args()
    # app = DataChunk(chunk_size = args.chunk_size)
    # item = []
    # num = 0
    # for i,path in enumerate(tqdm(glob('result/*/wiki_*'))):
    #     ret = app.chunk(path)
    #     # item.append(max([len(e) for e in ret]))
    #     num += len(ret)
    #     # if i > 9 : break
    # print(f'total number of passages : {num}')
    # print(f"max length of passage : {max(item)}")
    save_orig_passage()
    save_title_index_map()