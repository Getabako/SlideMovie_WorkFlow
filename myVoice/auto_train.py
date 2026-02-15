#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPT-SoVITS 自動学習スクリプト (Mac Apple Silicon対応)
WebUIを使わずに一発で学習を完走させるスクリプト

使用方法:
    cd /path/to/GPT-SoVITS
    conda activate GPTSoVits
    python auto_train.py
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

# ============================================
# 設定 (ハードコーディング)
# ============================================

# 入力音声ファイル
INPUT_AUDIO = os.path.expanduser("~/Desktop/myvoice.mp3")

# 実験名 (モデル名)
EXP_NAME = "my_voice"

# バージョン (v1が最も安定・軽量)
VERSION = "v1"

# 出力ディレクトリ
OUTPUT_DIR = "output"
SLICED_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "sliced_audio")
ASR_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "asr_opt")

# ASR設定
ASR_MODEL_SIZE = "medium"
ASR_LANGUAGE = "ja"
ASR_PRECISION = "float32"  # Macではfloat32必須

# スライス設定
SLICE_THRESHOLD = -34      # 音量閾値 (dB)
SLICE_MIN_LENGTH = 4000    # 最小長 (ms)
SLICE_MIN_INTERVAL = 300   # 最小間隔 (ms)
SLICE_HOP_SIZE = 10        # ホップサイズ (ms)
SLICE_MAX_SIL_KEPT = 500   # 最大無音保持 (ms)
SLICE_MAX = 0.9            # 最大振幅
SLICE_ALPHA = 0.25         # アルファ

# 事前学習モデルパス
BERT_PRETRAINED_DIR = "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large"
SSL_PRETRAINED_DIR = "GPT_SoVITS/pretrained_models/chinese-hubert-base"
PRETRAINED_S2G = "GPT_SoVITS/pretrained_models/s2G488k.pth"
PRETRAINED_S2D = "GPT_SoVITS/pretrained_models/s2D488k.pth"
PRETRAINED_S1 = "GPT_SoVITS/pretrained_models/s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt"

# 学習設定 (Mac用に軽量設定)
SOVITS_EPOCHS = 8
SOVITS_BATCH_SIZE = 2
SOVITS_SAVE_EVERY_EPOCH = 4
GPT_EPOCHS = 10
GPT_BATCH_SIZE = 2
GPT_SAVE_EVERY_EPOCH = 5

# Mac設定
IS_HALF = False  # float32を使用


# ============================================
# ユーティリティ関数
# ============================================

def run_command(cmd, description=""):
    """コマンドを実行して結果を表示"""
    print(f"\n{'='*60}")
    print(f"[STEP] {description}")
    print(f"{'='*60}")
    print(f"Command: {cmd}\n")

    result = subprocess.run(cmd, shell=True)

    if result.returncode != 0:
        print(f"[ERROR] {description} failed with return code {result.returncode}")
        return False

    print(f"[OK] {description} completed successfully")
    return True


def setup_environment():
    """環境変数を設定"""
    # GPT-SoVITSのルートディレクトリを取得
    now_dir = os.path.dirname(os.path.abspath(__file__))

    # PYTHONPATHを設定
    paths_to_add = [
        now_dir,
        os.path.join(now_dir, "GPT_SoVITS"),
        os.path.join(now_dir, "GPT_SoVITS", "BigVGAN"),
        os.path.join(now_dir, "tools"),
        os.path.join(now_dir, "tools", "asr"),
        os.path.join(now_dir, "tools", "uvr5"),
    ]

    for path in paths_to_add:
        if path not in sys.path:
            sys.path.insert(0, path)

    # TEMPディレクトリを作成
    tmp_dir = os.path.join(now_dir, "TEMP")
    os.makedirs(tmp_dir, exist_ok=True)
    os.environ["TEMP"] = tmp_dir

    return now_dir


def check_prerequisites():
    """前提条件をチェック"""
    print("\n[CHECK] Checking prerequisites...")

    # 入力音声ファイルの確認
    if not os.path.exists(INPUT_AUDIO):
        print(f"[ERROR] Input audio file not found: {INPUT_AUDIO}")
        return False
    print(f"  - Input audio: OK ({INPUT_AUDIO})")

    # 事前学習モデルの確認
    models = [
        ("BERT", BERT_PRETRAINED_DIR),
        ("SSL (HuBERT)", SSL_PRETRAINED_DIR),
        ("SoVITS G", PRETRAINED_S2G),
        ("SoVITS D", PRETRAINED_S2D),
        ("GPT", PRETRAINED_S1),
    ]

    for name, path in models:
        if not os.path.exists(path):
            print(f"[ERROR] {name} model not found: {path}")
            return False
        print(f"  - {name}: OK")

    print("[CHECK] All prerequisites OK")
    return True


# ============================================
# Step 1: 音声スライス
# ============================================

def step1_slice_audio():
    """音声ファイルをスライス"""
    os.makedirs(SLICED_OUTPUT_DIR, exist_ok=True)

    python_exec = sys.executable
    cmd = (
        f'"{python_exec}" -s tools/slice_audio.py '
        f'"{INPUT_AUDIO}" '
        f'"{SLICED_OUTPUT_DIR}" '
        f'{SLICE_THRESHOLD} '
        f'{SLICE_MIN_LENGTH} '
        f'{SLICE_MIN_INTERVAL} '
        f'{SLICE_HOP_SIZE} '
        f'{SLICE_MAX_SIL_KEPT} '
        f'{SLICE_MAX} '
        f'{SLICE_ALPHA} '
        f'0 1'  # i_part, all_part
    )

    return run_command(cmd, "Step 1: Audio Slicing")


# ============================================
# Step 2: 音声認識 (ASR)
# ============================================

def step2_asr():
    """スライスした音声を文字起こし"""
    os.makedirs(ASR_OUTPUT_DIR, exist_ok=True)

    python_exec = sys.executable
    cmd = (
        f'"{python_exec}" -s tools/asr/fasterwhisper_asr.py '
        f'-i "{SLICED_OUTPUT_DIR}" '
        f'-o "{ASR_OUTPUT_DIR}" '
        f'-s {ASR_MODEL_SIZE} '
        f'-l {ASR_LANGUAGE} '
        f'-p {ASR_PRECISION}'
    )

    return run_command(cmd, "Step 2: ASR (Speech Recognition)")


# ============================================
# Step 3: データセット準備
# ============================================

def step3_prepare_dataset():
    """学習用データセットを準備"""

    # ASR出力ファイルパスを取得
    sliced_folder_name = os.path.basename(SLICED_OUTPUT_DIR)
    asr_list_path = os.path.join(ASR_OUTPUT_DIR, f"{sliced_folder_name}.list")

    if not os.path.exists(asr_list_path):
        print(f"[ERROR] ASR output not found: {asr_list_path}")
        return False

    # 実験ディレクトリを作成
    exp_dir = os.path.join("logs", EXP_NAME)
    os.makedirs(exp_dir, exist_ok=True)
    os.makedirs(os.path.join(exp_dir, "logs_s1"), exist_ok=True)
    os.makedirs(os.path.join(exp_dir, f"logs_s2_{VERSION}"), exist_ok=True)

    python_exec = sys.executable

    # --- Step 3a: テキスト分割とBERT抽出 ---
    print("\n[STEP 3a] Text processing and BERT extraction...")

    env_3a = os.environ.copy()
    env_3a.update({
        "inp_text": asr_list_path,
        "inp_wav_dir": SLICED_OUTPUT_DIR,
        "exp_name": EXP_NAME,
        "opt_dir": exp_dir,
        "bert_pretrained_dir": BERT_PRETRAINED_DIR,
        "i_part": "0",
        "all_parts": "1",
        "is_half": str(IS_HALF),
        "_CUDA_VISIBLE_DEVICES": "",
        "version": VERSION,
    })

    cmd = f'"{python_exec}" -s GPT_SoVITS/prepare_datasets/1-get-text.py'
    result = subprocess.run(cmd, shell=True, env=env_3a)

    if result.returncode != 0:
        print("[ERROR] Step 3a failed")
        return False

    # 結果ファイルをマージ
    txt_path = os.path.join(exp_dir, "2-name2text-0.txt")
    path_text = os.path.join(exp_dir, "2-name2text.txt")
    if os.path.exists(txt_path):
        shutil.move(txt_path, path_text)
    print("[OK] Step 3a completed")

    # --- Step 3b: SSL特徴抽出 (HuBERT) ---
    print("\n[STEP 3b] SSL feature extraction (HuBERT)...")

    env_3b = os.environ.copy()
    env_3b.update({
        "inp_text": asr_list_path,
        "inp_wav_dir": SLICED_OUTPUT_DIR,
        "exp_name": EXP_NAME,
        "opt_dir": exp_dir,
        "cnhubert_base_dir": SSL_PRETRAINED_DIR,
        "i_part": "0",
        "all_parts": "1",
        "is_half": str(IS_HALF),
        "_CUDA_VISIBLE_DEVICES": "",
    })

    cmd = f'"{python_exec}" -s GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py'
    result = subprocess.run(cmd, shell=True, env=env_3b)

    if result.returncode != 0:
        print("[ERROR] Step 3b failed")
        return False
    print("[OK] Step 3b completed")

    # --- Step 3c: セマンティックトークン抽出 ---
    print("\n[STEP 3c] Semantic token extraction...")

    s2_config = "GPT_SoVITS/configs/s2.json"

    env_3c = os.environ.copy()
    env_3c.update({
        "inp_text": asr_list_path,
        "exp_name": EXP_NAME,
        "opt_dir": exp_dir,
        "pretrained_s2G": PRETRAINED_S2G,
        "s2config_path": s2_config,
        "i_part": "0",
        "all_parts": "1",
        "is_half": str(IS_HALF),
        "_CUDA_VISIBLE_DEVICES": "",
    })

    cmd = f'"{python_exec}" -s GPT_SoVITS/prepare_datasets/3-get-semantic.py'
    result = subprocess.run(cmd, shell=True, env=env_3c)

    if result.returncode != 0:
        print("[ERROR] Step 3c failed")
        return False

    # 結果ファイルをマージ
    semantic_path = os.path.join(exp_dir, "6-name2semantic-0.tsv")
    path_semantic = os.path.join(exp_dir, "6-name2semantic.tsv")
    if os.path.exists(semantic_path):
        with open(semantic_path, "r", encoding="utf8") as f:
            content = f.read()
        with open(path_semantic, "w", encoding="utf8") as f:
            f.write("item_name\tsemantic_audio\n" + content)
        os.remove(semantic_path)
    print("[OK] Step 3c completed")

    return True


# ============================================
# Step 4: SoVITS学習
# ============================================

def step4_train_sovits():
    """SoVITSモデルを学習"""

    exp_dir = os.path.join("logs", EXP_NAME)
    python_exec = sys.executable

    # 設定ファイルを読み込み
    config_file = "GPT_SoVITS/configs/s2.json"
    with open(config_file, "r") as f:
        data = json.load(f)

    # Mac用の設定を上書き
    data["train"]["fp16_run"] = False  # float32
    data["train"]["batch_size"] = SOVITS_BATCH_SIZE
    data["train"]["epochs"] = SOVITS_EPOCHS
    data["train"]["save_every_epoch"] = SOVITS_SAVE_EVERY_EPOCH
    data["train"]["text_low_lr_rate"] = 0.4
    data["train"]["pretrained_s2G"] = PRETRAINED_S2G
    data["train"]["pretrained_s2D"] = PRETRAINED_S2D
    data["train"]["if_save_latest"] = True
    data["train"]["if_save_every_weights"] = True
    data["train"]["gpu_numbers"] = "0"
    data["train"]["grad_ckpt"] = False
    data["train"]["lora_rank"] = 0
    data["model"]["version"] = VERSION
    data["data"]["exp_dir"] = exp_dir
    data["s2_ckpt_dir"] = exp_dir
    data["save_weight_dir"] = "SoVITS_weights"
    data["name"] = EXP_NAME
    data["version"] = VERSION

    # 一時設定ファイルを保存
    tmp_config = os.path.join("TEMP", "tmp_s2.json")
    os.makedirs("TEMP", exist_ok=True)
    with open(tmp_config, "w") as f:
        json.dump(data, f, indent=2)

    # SoVITS学習を実行
    cmd = f'"{python_exec}" -s GPT_SoVITS/s2_train.py --config "{tmp_config}"'

    return run_command(cmd, "Step 4: SoVITS Training")


# ============================================
# Step 5: GPT学習
# ============================================

def step5_train_gpt():
    """GPTモデルを学習"""

    exp_dir = os.path.join("logs", EXP_NAME)
    python_exec = sys.executable

    # YAML設定を読み込み
    import yaml

    config_file = "GPT_SoVITS/configs/s1longer.yaml"
    with open(config_file, "r") as f:
        data = yaml.safe_load(f)

    # Mac用の設定を上書き
    data["train"]["precision"] = "32"  # float32
    data["train"]["batch_size"] = GPT_BATCH_SIZE
    data["train"]["epochs"] = GPT_EPOCHS
    data["train"]["save_every_n_epoch"] = GPT_SAVE_EVERY_EPOCH
    data["train"]["if_save_every_weights"] = True
    data["train"]["if_save_latest"] = True
    data["train"]["if_dpo"] = False
    data["train"]["half_weights_save_dir"] = "GPT_weights"
    data["train"]["exp_name"] = EXP_NAME
    data["pretrained_s1"] = PRETRAINED_S1
    data["train_semantic_path"] = os.path.join(exp_dir, "6-name2semantic.tsv")
    data["train_phoneme_path"] = os.path.join(exp_dir, "2-name2text.txt")
    data["output_dir"] = os.path.join(exp_dir, f"logs_s1_{VERSION}")

    # 一時設定ファイルを保存
    tmp_config = os.path.join("TEMP", "tmp_s1.yaml")
    os.makedirs("TEMP", exist_ok=True)
    with open(tmp_config, "w") as f:
        yaml.dump(data, f, default_flow_style=False)

    # GPT学習を実行
    os.environ["_CUDA_VISIBLE_DEVICES"] = ""
    os.environ["hz"] = "25hz"

    cmd = f'"{python_exec}" -s GPT_SoVITS/s1_train.py --config_file "{tmp_config}"'

    return run_command(cmd, "Step 5: GPT Training")


# ============================================
# メイン処理
# ============================================

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║         GPT-SoVITS Auto Training Script                   ║
║              (Mac Apple Silicon Edition)                   ║
╚════════════════════════════════════════════════════════════╝
    """)

    print(f"Input Audio: {INPUT_AUDIO}")
    print(f"Model Name: {EXP_NAME}")
    print(f"Version: {VERSION}")
    print(f"Precision: float32 (Mac compatible)")
    print(f"SoVITS: {SOVITS_EPOCHS} epochs, batch size {SOVITS_BATCH_SIZE}")
    print(f"GPT: {GPT_EPOCHS} epochs, batch size {GPT_BATCH_SIZE}")

    # 環境設定
    now_dir = setup_environment()
    os.chdir(now_dir)
    print(f"\nWorking directory: {now_dir}")

    # 前提条件チェック
    if not check_prerequisites():
        print("\n[ABORT] Prerequisites check failed. Please fix the issues and try again.")
        sys.exit(1)

    # Step 1: 音声スライス
    if not step1_slice_audio():
        print("\n[ABORT] Audio slicing failed.")
        sys.exit(1)

    # Step 2: ASR
    if not step2_asr():
        print("\n[ABORT] ASR failed.")
        sys.exit(1)

    # Step 3: データセット準備
    if not step3_prepare_dataset():
        print("\n[ABORT] Dataset preparation failed.")
        sys.exit(1)

    # Step 4: SoVITS学習
    if not step4_train_sovits():
        print("\n[ABORT] SoVITS training failed.")
        sys.exit(1)

    # Step 5: GPT学習
    if not step5_train_gpt():
        print("\n[ABORT] GPT training failed.")
        sys.exit(1)

    # 完了メッセージ
    print("""
╔════════════════════════════════════════════════════════════╗
║                   Training Complete!                       ║
╚════════════════════════════════════════════════════════════╝
    """)
    print("Your trained models are saved in:")
    print(f"  - SoVITS: SoVITS_weights/{EXP_NAME}_*.pth")
    print(f"  - GPT:    GPT_weights/{EXP_NAME}_*.ckpt")
    print("")
    print("To use your voice model for inference, load these files in the inference WebUI.")


if __name__ == "__main__":
    main()
