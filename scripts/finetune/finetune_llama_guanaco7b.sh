python qlora_finetune.py \
    --model_name_or_path decapoda-research/llama-7b-hf \
    --dataset_name oasst1 \
    --data_dir /home/robin/prompt_data/ \
    --load_from_local \
    --output_dir ./work_dir/oasst1-llama-7b \
    --num_train_epochs 3 \
    --per_device_train_batch_size 4 \
    --per_device_eval_batch_size 4 \
    --gradient_accumulation_steps 8 \
    --evaluation_strategy steps \
    --eval_steps 200 \
    --save_strategy steps \
    --save_total_limit 5 \
    --save_steps 100 \
    --logging_strategy steps \
    --logging_steps 1 \
    --learning_rate 0.0002 \
    --warmup_ratio 0.03 \
    --weight_decay 0.0 \
    --lr_scheduler_type constant \
    --adam_beta2 0.999 \
    --max_grad_norm 0.3 \
    --max_new_tokens 32 \
    --source_max_len 512 \
    --target_max_len 512 \
    --lora_r 64 \
    --lora_alpha 16 \
    --lora_dropout 0.1 \
    --double_quant \
    --quant_type nf4 \
    --fp16 \
    --bits 4 \
    --gradient_checkpointing \
    --do_train \
    --do_eval \
    --sample_generate \
    --data_seed 42 \
    --seed 0