import argparse
import os
import time

import torch
import transformers
from transformers import GenerationConfig, Trainer, set_seed

from chatllms.data.conv_dataset import make_conversation_data_module
from chatllms.data.sft_dataset import make_supervised_data_module
from chatllms.model.load_pretrain_model import load_model_tokenizer
from chatllms.model.save_peft_model_callback import SavePeftModelCallback
from chatllms.utils.callbacks import MMLUEvalCallback, SampleGenerateCallback
from chatllms.utils.config import (DataArguments, GenerationArguments,
                                   LoraArguments, ModelArguments,
                                   QuantArgments, TrainingArguments)
from chatllms.utils.logging import get_root_logger
from chatllms.utils.model_utils import (add_special_tokens_if_missing,
                                        get_last_checkpoint,
                                        print_trainable_parameters,
                                        verify_dtypes)
from chatllms.utils.training import train_and_evaluate

torch.backends.cuda.matmul.allow_tf32 = True


def main():
    parser = transformers.HfArgumentParser(
        (ModelArguments, DataArguments, TrainingArguments, LoraArguments,
         QuantArgments, GenerationArguments))
    (model_args, data_args, training_args, lora_args, quant_args,
     generation_args) = parser.parse_args_into_dataclasses()
    training_args.generation_config = GenerationConfig(**vars(generation_args))

    args = argparse.Namespace(**vars(model_args), **vars(data_args),
                              **vars(training_args), **vars(lora_args),
                              **vars(quant_args))

    # init the logger before other steps
    timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    log_file = os.path.join(args.output_dir, f'{timestamp}.log')
    logger = get_root_logger(log_file=log_file, log_level='INFO')

    logger.info('Training/evaluation parameters %s', args)
    # Check if training was already completed.
    checkpoint_dir, completed_training = get_last_checkpoint(args.output_dir)
    args.checkpoint_dir = checkpoint_dir
    if completed_training:
        logger.info('=' * 40, 'Attention', '=' * 40)
        logger.info('Detected that training was already completed!')

    # # load model and tokenizer
    model, tokenizer = load_model_tokenizer(
        args=args,
        checkpoint_dir=checkpoint_dir,
        is_trainable=args.do_train,
        logger=logger,
    )
    logger.info('Loaded model...')

    logger.info('Printing trainable parameters...')
    print_trainable_parameters(args, model)

    set_seed(args.seed)
    # LLaMA tokenizer may not have correct special tokens set.
    # Check and add them if missing to prevent them from being parsed into different tokens.
    # Note that these are present in the vocabulary.
    # Note also that `model.config.pad_token_id` is 0 which corresponds to `<unk>` token.
    logger.info('Adding special tokens.')
    if 'llama' in args.model_name_or_path or 'baichuan' in args.model_name_or_path:
        add_special_tokens_if_missing(tokenizer, model)

    # Verify dtypes
    logger.info('Verifying dtypes...')
    verify_dtypes(model)

    if not args.multiturn_dialogue:
        logger.info('Training data is not a multiturn dialogue formate')
        data_module = make_supervised_data_module(tokenizer=tokenizer,
                                                  args=args)
    else:
        logger.info('Training data is a multiturn dialogue formate')
        data_module = make_conversation_data_module(
            tokenizer=tokenizer,
            lazy_preprocess=args.lazy_preprocess,
            data_path=args.data_path)

    trainer = Trainer(model=model,
                      tokenizer=tokenizer,
                      args=training_args,
                      **data_module)
    # Add callback to save adapter model.
    if not args.full_finetune:
        trainer.add_callback(SavePeftModelCallback)

    # Add callback to generate samples.
    if args.sample_generate:
        trainer.add_callback(
            SampleGenerateCallback(
                tokenizer=tokenizer,
                generation_config=GenerationConfig(**vars(generation_args)),
                logger=logger,
            ))

    if args.do_mmlu_eval:
        eval_callback = MMLUEvalCallback(
            trainer=trainer,
            tokenizer=tokenizer,
            data_dir='./data',
            args=args,
        )
        trainer.add_callback(eval_callback)

    assert args.do_train or args.do_eval or args.do_predict
    if args.do_train or args.do_eval:
        train_and_evaluate(trainer, args, logger)


if __name__ == '__main__':
    main()
