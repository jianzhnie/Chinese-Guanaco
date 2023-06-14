from typing import Any, Dict, Optional, Union

import numpy as np
from datasets import Dataset, load_dataset

ALPACA_PROMPT_DICT = {
    'prompt_input':
    ('Below is an instruction that describes a task, paired with an input that provides further context. '
     'Write a response that appropriately completes the request.\n\n'
     '### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response: '
     ),
    'prompt_no_input':
    ('Below is an instruction that describes a task. '
     'Write a response that appropriately completes the request.\n\n'
     '### Instruction:\n{instruction}\n\n### Response: '),
}


def load_data(dataset_name: str) -> Union[Dict[str, Dataset], None]:
    """
    Load a dataset based on its name.

    Args:
        dataset_name: A string representing the name of the dataset to be loaded.

    Returns:
        A dictionary containing the loaded dataset if the dataset exists.
        None if the dataset does not exist.

    Raises:
        NotImplementedError: If the dataset name provided is not implemented yet or if
            the dataset is not released.

    Examples:
        >>> load_data('alpaca')
        {'train': Dataset(...), 'validation': Dataset(...), 'test': Dataset(...)}

    """
    if dataset_name == 'alpaca':
        return load_dataset('tatsu-lab/alpaca')
    elif dataset_name == 'alpaca-clean':
        return load_dataset('yahma/alpaca-cleaned')
    elif dataset_name == 'chip2':
        return load_dataset('laion/OIG', data_files='unified_chip2.jsonl')
    elif dataset_name == 'self-instruct':
        return load_dataset('yizhongw/self_instruct', name='self_instruct')
    elif dataset_name == 'hh-rlhf':
        return load_dataset('Anthropic/hh-rlhf')
    elif dataset_name == 'longform':
        return load_dataset('akoksal/LongForm')
    elif dataset_name == 'oasst1':
        return load_dataset('timdettmers/openassistant-guanaco')
    elif dataset_name == 'vicuna':
        raise NotImplementedError('Vicuna data was not released.')
    else:
        raise NotImplementedError(
            f'Dataset {dataset_name} not implemented yet.')


def extract_alpaca_dataset(example: Dict[str, Any]) -> Dict[str, str]:
    """
    Extracts input from an example in the Alpaca dataset.

    Args:
        example: A dictionary containing a single example from the Alpaca dataset.

    Returns:
        A dictionary containing the extracted input string from the example.

    Examples:
        >>> example = {'input': 'example input', 'output': 'example output'}
        >>> extract_alpaca_dataset(example)
        {'input': 'example input'}

    """
    if example.get('input', '') != '':
        prompt_format = ALPACA_PROMPT_DICT['prompt_input']
    else:
        prompt_format = ALPACA_PROMPT_DICT['prompt_no_input']
    return {'input': prompt_format.format(**example)}


def format_dataset(dataset: Dataset,
                   dataset_name: str) -> Optional[Dict[str, Dataset]]:
    """
    Formats a given dataset based on its name and format.

    Args:
        dataset: A dataset object to be formatted.
        dataset_name: A string representing the name of the dataset to be formatted.

    Returns:
        A dictionary containing the formatted dataset if the dataset exists in the
        specified format.
        None if the dataset does not exist or if the format is not recognized.

    Examples:
        >>> format_dataset('alpaca')
        {'train': Dataset(...), 'validation': Dataset(...), 'test': Dataset(...)}

    """
    if dataset_name == 'alpaca' or dataset_name == 'alpaca-clean':
        dataset = dataset.map(extract_alpaca_dataset,
                              remove_columns=['instruction'])
    elif dataset_name == 'chip2':
        dataset = dataset.map(
            lambda x: {
                'input': x['text'].split('\n<bot>: ')[0].replace(
                    '<human>: ', ''),
                'output': x['text'].split('\n<bot>: ')[1]
            })
    elif dataset_name == 'self-instruct':
        dataset = dataset.rename_column('prompt', 'input')
        dataset = dataset.rename_column('completion', 'output')
    elif dataset_name == 'hh-rlhf':
        dataset = dataset.map(lambda x: {'input': '', 'output': x['chosen']})
    elif dataset_name == 'oasst1':
        dataset = dataset.map(lambda x: {'input': '', 'output': x['text']})
    elif dataset_name == 'input-output':
        pass
    else:
        return None  # invalid format

    # Remove unused columns.
    dataset = dataset.remove_columns([
        col for col in dataset.column_names['train']
        if col not in ['input', 'output']
    ])
    return dataset


def split_train_eval(
    dataset: Dataset,
    do_eval: bool = False,
    eval_dataset_size: float = 0.2,
    max_eval_samples: int = None,
    group_by_length: bool = False,
    do_train: bool = True,
    max_train_samples: int = None,
) -> Dict[str, Dataset]:
    """
    Prepare the training and evaluation datasets for a machine learning model.

    Args:
        dataset (DatasetDict): The complete dataset containing train, validation, and test splits.
        do_eval (bool, optional): Whether to use an evaluation dataset or not. Defaults to False.
        eval_dataset_size (float, optional): The size of the validation set if splitting from the training data.
            Ignored if `do_eval` is False. Defaults to 0.2.
        max_eval_samples (int, optional): The maximum number of samples to keep in the evaluation dataset.
            Ignored if `do_eval` is False or `None`. Defaults to None.
        group_by_length (bool, optional): Whether to group the data by length or not. Defaults to False.
        do_train (bool, optional): Whether to use a training dataset or not. Defaults to True.
        max_train_samples (int, optional): The maximum number of samples to keep in the training dataset.
            Ignored if `do_train` is False or `None`. Defaults to None.

    Returns:
        Dict[str, Dataset]: A dictionary containing the prepared training and evaluation datasets
        (if used), where the keys are 'train' and 'eval', respectively.
    """
    if not isinstance(dataset, Dataset):
        raise TypeError("The 'dataset' argument must be a DatasetDict object.")

    # Prepare evaluation dataset
    if do_eval:
        if 'eval' in dataset:
            eval_dataset = dataset['eval']
        else:
            # Split train dataset in train and validation according to `eval_dataset_size`
            print(
                'Splitting train dataset in train and validation according to `eval_dataset_size`'
            )
            dataset = dataset['train'].train_test_split(
                test_size=eval_dataset_size, shuffle=True, seed=42)
            eval_dataset = dataset['test']

        # Reduce evaluation dataset size (if specified)
        if max_eval_samples is not None and len(
                eval_dataset) > max_eval_samples:
            eval_dataset = eval_dataset.select(np.arange(max_eval_samples))

        # Group data by length (if specified)
        if group_by_length:
            eval_dataset = eval_dataset.map(
                lambda x: {'length': len(x['input']) + len(x['output'])})

    # Prepare training dataset
    if do_train:
        train_dataset = dataset['train']

        # Reduce training dataset size (if specified)
        if max_train_samples is not None and len(
                train_dataset) > max_train_samples:
            train_dataset = train_dataset.select(np.arange(max_train_samples))

        # Group data by length (if specified)
        if group_by_length:
            train_dataset = train_dataset.map(
                lambda x: {'length': len(x['input']) + len(x['output'])})

    return {
        'train': train_dataset if do_train else None,
        'eval': eval_dataset if do_eval else None
    }


def load_and_format_dataset(data_path: str) -> Dataset:
    """
    Load a dataset from the `data_path` argument and format each example using a pre-defined prompt specified in
    `ALPACA_PROMPT_DICT`. The formatted examples will only include an input prompt and corresponding output.

    Args:
    - data_path (str): A string representing the path to the dataset.

    Returns:
    - A Hugging Face datasets Dataset containing formatted examples.
    """

    # Define the prompts that will be used to format each example
    ALPACA_PROMPT_DICT: Dict[str, str] = {
        'prompt_input':
        ('Below is an instruction that describes a task, paired with an input that provides '
         'further context. Write a response that appropriately completes the request.\n\n'
         '### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response: '
         ),
        'prompt_no_input':
        ('Below is an instruction that describes a task. Write a response that appropriately '
         'completes the request.\n\n### Instruction:\n{instruction}\n\n### Response: '
         )
    }

    def extract_alpaca_dataset(example: Dict[str, str]) -> Dict[str, str]:
        """
        This function formats a single input-output example using the appropriate prompt.

        Args:
        - example (Dict[str, str]): A dictionary representing a single example containing the keys 'input',
          'output', and 'instruction'.

        Returns:
        - A dictionary containing the formatted input and output for the given example.
        """
        if example.get('input', '') != '':
            prompt_format = ALPACA_PROMPT_DICT['prompt_input']
        else:
            prompt_format = ALPACA_PROMPT_DICT['prompt_no_input']
        return {'input': prompt_format.format(**example)}

    # Load the dataset from the given data path
    if data_path.endswith('.json') or data_path.endswith('.jsonl'):
        dataset = load_dataset('json', data_files=data_path)['train']
    else:
        dataset = load_dataset(
            data_path, cache_dir='~/.cache/huggingface/datasets')['train']

    # Map each example to a formatted input-output pair using the `extract_alpaca_dataset` function
    dataset = dataset.map(extract_alpaca_dataset,
                          remove_columns=['instruction'])

    # Remove any unused columns (only 'input' and 'output' will remain)
    dataset = dataset.remove_columns([
        col for col in dataset.column_names if col not in ['input', 'output']
    ])

    return dataset