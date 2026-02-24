import pytest
from core.passwords import validate_password, hash_password, verify_password
from core.exceptions import InvalidPasswordError
from config import MIN_LENGTH, MIN_UPPER, MIN_LOWER, MIN_DIGITS, MIN_SYMBOLS, SYMBOLS

# ---------------------------
# VALIDATE PASSWORD
# ---------------------------

def test_validate_password_too_short():
    pw = "A1a!" 
    with pytest.raises(InvalidPasswordError, match=f"Password must be at least {MIN_LENGTH} characters"):
        validate_password(pw)

def test_validate_password_no_uppercase():
    pw = "a" * MIN_LENGTH + "1!"  
    with pytest.raises(InvalidPasswordError, match=f"Password must contain at least {MIN_UPPER} uppercase letters"):
        validate_password(pw)

def test_validate_password_no_lowercase():
    pw = "A" * MIN_LENGTH + "1!"  
    with pytest.raises(InvalidPasswordError, match=f"Password must contain at least {MIN_LOWER} lowercase letters"):
        validate_password(pw)

def test_validate_password_no_digits():
    pw = "Aa" * (MIN_LENGTH // 2) + "!"  
    with pytest.raises(InvalidPasswordError, match=f"Password must contain at least {MIN_DIGITS} digits"):
        validate_password(pw)

def test_validate_password_no_symbols():
    pw = "Aa1" * (MIN_LENGTH // 3)  
    with pytest.raises(InvalidPasswordError, match=f"Password must contain at least {MIN_SYMBOLS} symbols"):
        validate_password(pw)

def test_validate_password_valid():
    
    pw = "A" * MIN_UPPER + "a" * MIN_LOWER + "1" * MIN_DIGITS + SYMBOLS[0] * MIN_SYMBOLS

    if len(pw) < MIN_LENGTH:
        pw += "x" * (MIN_LENGTH - len(pw))
    validate_password(pw)

# ---------------------------
# HASH PASSWORD
# ---------------------------

def test_hash_password_generates_hash():
    pw = "Aa1!" * 4  
    hashed = hash_password(pw)
    assert hashed != pw 
    assert isinstance(hashed, str)

# ---------------------------
# VERIFY PASSWORD
# ---------------------------

def test_verify_password_correct():
    pw = "Aa1!" * 4
    hashed = hash_password(pw)
    assert verify_password(pw, hashed) is True

def test_verify_password_incorrect():
    pw = "Aa1!" * 4
    hashed = hash_password(pw)
    wrong_pw = "Bb2@" * 4
    assert verify_password(wrong_pw, hashed) is False