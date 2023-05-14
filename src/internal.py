import hashlib
import os

GIT_DIR = ".pygit"
CURRENT_DIR = "testing"


def init():
    if not os.path.exists(GIT_DIR):
        os.makedirs(GIT_DIR)
    if not os.path.exists(f"{GIT_DIR}/objects"):
        os.makedirs(f"{GIT_DIR}/objects")


def get_ignored():
    with open(".pygitignore", "r") as f:
        return set([f"./{path}" for path in f.read().split("\n")])


def get_object(object_id, expected_type="blob"):
    with open(f"{GIT_DIR}/objects/{object_id}", "rb") as f:
        object = f.read()
    type_, _, content = object.partition(b"\x00")

    type_ = type_.decode()
    content = content.decode()

    if expected_type is not None:
        assert expected_type == type_, f"Expected {expected_type}, got {type_}"
    return content


def hash_object(data, type_="blob"):
    content = type_.encode() + b"\x00" + data
    object_id = hashlib.sha1(content).hexdigest()

    with open(f"{GIT_DIR}/objects/{object_id}", "wb") as out:
        out.write(content)

    return object_id


def restore_tree(object_id, current_dir=CURRENT_DIR):
    objects = get_object(object_id, None).strip().split("\n")
    for object in objects:
        type_, object_id, object_path = object.split(" ")
        current_path = f"{current_dir}/{object_path}"
        if type_ == "blob":
            content = get_object(object_id, "blob")
            os.makedirs(os.path.dirname(current_path), exist_ok=True)
            with open(current_path, "w") as out:
                out.write(content)

        if type_ == "tree":
            restore_tree(object_id, current_path)


def write_tree(dir=CURRENT_DIR):
    ignored = get_ignored()

    def _write_tree(dir):
        objects = []
        with os.scandir(dir) as it:
            for entry in it:
                full_path = f"{dir}/{entry.name}"

                if full_path in ignored:
                    continue

                if entry.is_file(follow_symlinks=False):
                    type_ = "blob"
                    with open(full_path, "rb") as f:
                        data = f.read()
                        object_id = hash_object(data, "blob")

                elif entry.is_dir(follow_symlinks=False):
                    type_ = "tree"
                    object_id = _write_tree(full_path)

                objects.append((type_, object_id, entry.name))

            tree = "".join(
                f"{type_} {object_id} {name}\n"
                for type_, object_id, name in sorted(objects)
            )

            return hash_object(tree.encode(), "tree")

    return _write_tree(dir)
