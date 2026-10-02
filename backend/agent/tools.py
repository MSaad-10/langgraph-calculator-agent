from langchain.tools import tool


# Define tools
@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b

@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b

@tool
def divide(a: int, b: int) -> float | str:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    if b == 0:
        return "Divisor cannot be zero."    
    return a / b

@tool
def subtract(a: int | float, b: int | float) -> int | float:
    """Subtracts `b` from `a`.
    
    Args:
        a: First int
        b: Second int
    """
    return a - b

@tool
def power(a: int, b: int) -> int | str:
    """Raises `a` to the power of `b`.
    
    Args:
        a: Base int
        b: Exponent int
    """
    if a == 0 and b < 0:
        return "Cannot raise 0 to a negative power."
    return a ** b

@tool
def modulus(a: int, b: int) -> int | str:
    """Returns the remainder of `a` divided by `b`.
    
    Args:
        a: Dividend
        b: Divisor
    """
    if b == 0:
        return "Divisor cannot be zero."
    return a % b

@tool
def square_root(number: int | float) -> float | int | str:
    """Returns the square root of `number`.
    
    Args:
        number: Number to find the square root of
    """
    if number < 0:
        return "Number cannot be negative."
    return number ** 0.5

