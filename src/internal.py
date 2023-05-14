import hashlib
import os

GIT_DIR = ".pygit"

# Used for DEV mode, such that no source code is
# lost by running pygit locally with bugs.
CURRENT_DIR = "testing"


def init():
    if not os.path.exists(GIT_DIR):
        os.makedirs(GIT_DIR)
    if not os.path.exists(f"{GIT_DIR}/objects"):
        os.makedirs(f"{GIT_DIR}/objects")


def get_ignored():
    with open(".pygitignore", "r") as f:
        return set(row for row in f.read().split("\n") if not row.startswith("#"))


def get_head():
    if not os.path.exists(f"{GIT_DIR}/HEAD"):
        return None
    with open(f"{GIT_DIR}/HEAD", "rb") as f:
        return f.read().decode()


def set_head(object_id):
    with open(f"{GIT_DIR}/HEAD", "wb") as f:
        f.write(object_id.encode())


def checkout(object_id):
    restore_tree(object_id, commit=True)
    set_head(object_id)


def log(object_id):
    if object_id:
        try:
            head = get_object(object_id, "commit")
        except FileNotFoundError:
            print("fatal: unknown revision not in the working tree.")
            raise SystemExit(1)

    else:
        head = get_head()

    if head is None:
        print("No commits exists yet.")
        return

    current = head
    while current is not None:
        output = f"commit {current}\n"
        current_content = get_object(current, "commit")
        current = None
        output += current_content + "\n"
        for line in current_content.split("\n"):
            if line.startswith("parent"):
                current = line.split(" ")[1]
                break
        print(output)


def commit(msg, user, time, force=False):
    tree = write_tree()
    commit_content = f"tree {tree}\n"

    parent = get_head()
    if parent is not None:
        parent_tree = get_object(parent, "commit").split("\n")[0].split(" ")[1]
        if parent_tree == tree and not force:
            return "Nothing to commit, working tree clean"
        commit_content += f"parent {parent}\n"

    commit_content += f"author {user}\n" + f"time {time}\n\n" + msg
    revision = hash_object(commit_content.encode(), "commit")
    set_head(revision)
    return commit_content


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


def restore_tree(object_id, current_dir=CURRENT_DIR, commit=False):
    def _restore_tree(object_id, current_dir):
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
                _restore_tree(object_id, current_path)

    rm_rf_directory(current_dir)

    if commit:
        commit_content = get_object(object_id, None).strip().split("\n")
        _, object_id = commit_content[0].split(" ")
        _restore_tree(object_id, current_dir)
    else:
        _restore_tree(object_id, current_dir)


def rm_rf_directory(dir=CURRENT_DIR):
    ignored = get_ignored()

    def _rm_rf_directory(dir):
        if not os.path.exists(dir):
            return

        with os.scandir(dir) as it:
            for entry in it:
                full_path = f"{dir}/{entry.name}"
                if full_path in ignored:
                    continue

                if entry.is_file(follow_symlinks=False):
                    os.remove(entry)

                elif entry.is_dir(follow_symlinks=False):
                    _rm_rf_directory(full_path)

    _rm_rf_directory(dir)


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
