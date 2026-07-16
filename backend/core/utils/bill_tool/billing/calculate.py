from functools import reduce
from langchain.tools import tool

@tool
def add(*args: int) -> int:
    """Add multiple numbers
    Args:
        *args (int): Variable number of integers to add.
    Returns:
        int: The sum of all provided numbers.
    """
    return sum(args)

@tool
def multiply(*args: int) -> int:
    """Multiply multiple numbers
    Args:
        *args (int): Variable number of integers to multiply.
    Returns:
        int: The product of all provided numbers.
    """
    if not args:
        return 0
    result = 1
    for num in args:
        result *= num
    return result

@tool
def subtract(*args: int) -> int:
    """Subtract multiple numbers from left to right
    Args:
        *args (int): Variable number of integers. The first number is the minuend,
                     and subsequent numbers are subtracted from it in order.
    Returns:
        int: The result of sequential subtraction.
    Raises:
        ValueError: If fewer than 2 arguments are provided.
    """
    if len(args) < 2:
        raise ValueError("subtract requires at least 2 numbers")
    return reduce(lambda x, y: x - y, args)

@tool
def divide(*args: int) -> float:
    """Divide multiple numbers from left to right
    Args:
        *args (int): Variable number of integers. The first number is the dividend,
                     and subsequent numbers are divisors applied in order.
    Returns:
        float: The result of sequential division.
    Raises:
        ValueError: If fewer than 2 arguments are provided.
        ZeroDivisionError: If any divisor is zero.
    """
    if len(args) < 2:
        raise ValueError("divide requires at least 2 numbers")
    return reduce(lambda x, y: x / y, args)