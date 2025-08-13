#!/bin/bash

if [ $# -ne 2 ];then
    echo "Usage: $0 $ARG1 $ARG2";
    exit 1
fi

base_input_dir=$1

output_dir=$2

email_address="himihiromu@yahoo.co.jp"

tmp_folder_name="./tmp_${output_dir}"

mkdir "$tmp_folder_name"

find "$base_input_dir" -maxdepth 2 -name "*.pdf" -print0 | while IFS= read -r -d '' pdf_file
do
  pdf_file_name="${pdf_file}"
  uv run python pdf_to_txt.py "$pdf_file_name" -p "$tmp_folder_name" -r "$email_address"
  uv run python text_formatter.py "$tmp_folder_name" -m hybrid -o "$tmp_folder_name"
  file_name=$(basename "$pdf_file" .pdf)
  uv run python text_to_voicevox.py "$tmp_folder_name" --speaker-id 14 -o "${output_dir}/${file_name}"
  rm -f "${tmp_folder_name}\\*"
done

rm -Rf "$tmp_folder_name"
