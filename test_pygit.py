from subprocess import check_call, check_output

import pytest

from src.internal import get_object, hash_object

TESTING_DIR = "test_dir"


def shell(*args, capture_stdout=False, **kwargs):
    if capture_stdout:
        return check_output(args, **kwargs).decode()
    check_call(args, **kwargs)


def setup():
    shell("make", "clean")
    shell("rm", "-rf", TESTING_DIR)

    shell("mkdir", TESTING_DIR)
    shell("mkdir", f"{TESTING_DIR}/nested")
    with open(f"{TESTING_DIR}/config.cfg", "w") as f:
        f.write("dumb eslint rule here")
    with open(f"{TESTING_DIR}/nested/script1.py", "w") as f:
        f.write("print('PWND')")
    with open(f"{TESTING_DIR}/nested/secrets.gdpr", "w") as f:
        f.write("PROD CREDENTIALS")
    with open(f"{TESTING_DIR}/nested/main.py", "w") as f:
        f.write("if __name__ != 'main':\n    print('run anyway')")


def test_hash_object():
    with open(f"{TESTING_DIR}/config.cfg", "rb") as f:
        content = f.read()
        object_id = hash_object(content, "blob")
        assert object_id == "c92f5a2095564f8c5d6ac4f0f53c500064891ce5"

        content += b"extra bytes"
        object_id = hash_object(content, "blob")
        assert object_id != "c92f5a2095564f8c5d6ac4f0f53c500064891ce5"


def test_get_object():
    with open(f"{TESTING_DIR}/config.cfg", "rb") as f:
        content = f.read()
        object_id = hash_object(content, "blob")

        expected_content = content.decode()
        content = get_object(object_id, "blob")
        assert content == expected_content

        with pytest.raises(AssertionError):
            content = get_object(object_id, "tree")


@pytest.fixture(scope="session", autouse=True)
def destroy():
    yield
    shell("rm", "-rf", TESTING_DIR)
    shell("make", "clean")
