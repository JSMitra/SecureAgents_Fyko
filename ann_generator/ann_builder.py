"""
FYKO ANN builder — exact copy of the thesis (Utility.py) helper functions.

Provides:
    generate_ANN()      — build and quick-train a Keras Sequential ANN
    generate_aes_key()  — derive an AES-256 key from the trained model
"""

import hashlib
import random
import time
import uuid

import numpy as np
import tensorflow as tf
from keras import Sequential
from keras.layers import Dense
from keras.optimizers import SGD

# ---------------------------------------------------------------------------
# Hex → Binary lookup
# ---------------------------------------------------------------------------

HEX_TO_BINARY = {
    "0": "0000", "1": "0001", "2": "0010", "3": "0011",
    "4": "0100", "5": "0101", "6": "0110", "7": "0111",
    "8": "1000", "9": "1001", "a": "1010", "b": "1011",
    "c": "1100", "d": "1101", "e": "1110", "f": "1111",
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def get_binary_md5(input_string: str = "") -> str:
    md5_hash = hashlib.md5(input_string.encode("utf-8"))
    hex_string = md5_hash.hexdigest()
    binary_md5 = bin(int(hex_string, 16))[2:].zfill(128)
    return binary_md5


def get_utc_md5(utc_time: int = 0) -> str:
    return get_binary_md5(str(utc_time))


def interleave_two_arrays(arr1, arr2):
    return [element for pair in zip(arr1, arr2) for element in pair]


def join_binary_strings_as_array(
    binary_string1: str = "",
    binary_string2: str = "",
    one: int = 1,
    zero: int = 0,
):
    combined_arr = interleave_two_arrays(binary_string1, binary_string2)
    total_len = len(combined_arr)
    arr = [zero for _ in range(total_len)]
    for i in range(total_len):
        if combined_arr[i] == "1":
            arr[i] = one
    return arr


def convert_binary_string_to_hex_string(binary_string: str = "") -> str:
    binary_string_len = len(binary_string)
    leading_zeros_to_pad = binary_string_len % 4
    binary_string = (
        "".join(["0" for _ in range(leading_zeros_to_pad)]) + binary_string
    )
    binary_string_len = len(binary_string)
    hex_string = ""
    hex_string_len = binary_string_len // 4
    for i in range(hex_string_len):
        hex_string = hex_string + hex(int(binary_string[i * 4 : i * 4 + 4], 2))[2:]
    return hex_string


# ---------------------------------------------------------------------------
# ANN training
# ---------------------------------------------------------------------------


def do_quick_training(model, sample_size: int = 256, training_epochs: int = 10):
    inputs, outputs = [], []
    for _ in range(sample_size):
        random_string = str(uuid.uuid4())
        utc_time = int(time.time())
        inp = np.array(
            join_binary_strings_as_array(
                get_binary_md5(random_string), get_utc_md5(utc_time)
            )
        )
        inputs.append(inp)
        y = np.array([random.random() for _ in range(256)])
        outputs.append(y)

    inputs = np.array(inputs)
    outputs = np.array(outputs)
    model.fit(
        inputs,
        outputs,
        epochs=training_epochs,
        batch_size=sample_size,
        verbose=False,
    )
    return model


def generate_ANN(
    use_complex_model: bool = False,
    learning_rate: float = 0.05,
    quick_train: bool = True,
    quick_train_sample_size: int = 256,
    quick_train_training_epochs: int = 10,
):
    """Build a Keras Sequential ANN and optionally quick-train it."""
    model = Sequential()
    model.add(
        Dense(
            256,
            activation="tanh",
            input_dim=256,
            kernel_initializer="RandomNormal",
            bias_initializer="he_uniform",
        )
    )
    model.add(
        Dense(
            256,
            activation="tanh",
            kernel_initializer="RandomNormal",
            bias_initializer="he_uniform",
        )
    )
    model.add(
        Dense(
            256,
            activation="tanh",
            kernel_initializer="RandomNormal",
            bias_initializer="he_uniform",
        )
    )
    model.compile(
        loss="mse",
        optimizer=SGD(learning_rate=learning_rate),
        metrics=["accuracy", "mse"],
    )
    if quick_train:
        model = do_quick_training(
            model,
            sample_size=quick_train_sample_size,
            training_epochs=quick_train_training_epochs,
        )
    return model


# ---------------------------------------------------------------------------
# AES key derivation
# ---------------------------------------------------------------------------


def generate_aes_key(
    input_model,
    random_string: str = "",
    utc_time: str = "0",
):
    """Derive an AES-256 key from the trained model's output."""
    input_bits = join_binary_strings_as_array(
        get_binary_md5(random_string), get_utc_md5(utc_time)
    )
    input_bits_str = ["1" if i == 1 else "0" for i in input_bits]
    input_str = convert_binary_string_to_hex_string("".join(input_bits_str))
    input_arr = np.array(input_bits)
    input_arr = tf.expand_dims(input_arr, axis=0)
    y = input_model.predict(input_arr, verbose=False)
    raw_ann_output = np.array(y[0])
    mean_value = np.mean(raw_ann_output)
    aes_key_256 = ["1" if i > mean_value else "0" for i in raw_ann_output]
    aes_key_256_str = "".join(aes_key_256)
    aes_key_256_bits = [1 if i > mean_value else 0 for i in raw_ann_output]
    return (
        convert_binary_string_to_hex_string(aes_key_256_str),
        aes_key_256_bits,
        raw_ann_output,
        input_str,
    )
