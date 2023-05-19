import hashlib
import os

GIT_DIR = ".pygit"

# Used for DEV mode, such that no source code is
# lost by running pygit locally with bugs.
CURRENT_DIR = "testing"


COMMIT_MSG_PATH = f"{GIT_DIR}/COMMIT_EDITMSG"


def create_dir_or_file_if_not_exists(path, type_="dir"):
    try:
        if type_ == "dir":
            os.makedirs(path)
        if type_ == "file":
            open(path, "x")
        return True
    except FileExistsError:
        return False


def init():
    create_dir_or_file_if_not_exists(GIT_DIR)
    create_dir_or_file_if_not_exists(f"{GIT_DIR}/objects")
    create_dir_or_file_if_not_exists(f"{GIT_DIR}/refs")
    create_dir_or_file_if_not_exists(f"{GIT_DIR}/refs/heads")
    create_dir_or_file_if_not_exists(f"{GIT_DIR}/refs/tags")
    # needs to init 'main'
    create_dir_or_file_if_not_exists(f"{GIT_DIR}/HEAD", "file")
    # Needs correct permissions
    create_dir_or_file_if_not_exists(f"{GIT_DIR}/COMMIT_EDITMSG", "file")


def get_ignored():
    with open(".pygitignore", "r") as f:
        return set(row for row in f.read().split("\n") if not row.startswith("#"))


def get_current_branch():
    with open(f"{GIT_DIR}/HEAD", "rb") as f:
        return f.read().decode()


def set_current_branch(name):
    with open(f"{GIT_DIR}/HEAD", "w") as f:
        f.write(name)


def get_ref(ref_type, name):
    if not os.path.exists(f"{GIT_DIR}/refs/{ref_type}/{name}"):
        return None
    with open(f"{GIT_DIR}/refs/{ref_type}/{name}", "rb") as f:
        return f.read().decode()


def set_ref(object_id, ref_type, name):
    with open(f"{GIT_DIR}/refs/{ref_type}/{name}", "wb") as f:
        f.write(object_id.encode())


def branch(name):
    object_id = get_ref("heads", name)
    if object_id:
        print(f"Branch '{name}' already exists.")
        return

    current_branch = get_current_branch()
    object_id = get_ref("heads", current_branch)
    set_ref(object_id, "heads", name)
    set_current_branch(name)


def checkout(object_id_or_tag_or_branch):
    if os.path.exists(f"{GIT_DIR}/objects/{object_id_or_tag_or_branch}"):
        object_id = object_id_or_tag_or_branch
    elif os.path.exists(f"{GIT_DIR}/refs/heads/{object_id_or_tag_or_branch}"):
        with open(f"{GIT_DIR}/refs/heads/{object_id_or_tag_or_branch}", "rb") as f:
            object_id = f.read().decode()
            set_current_branch(object_id_or_tag_or_branch)
    elif os.path.exists(f"{GIT_DIR}/refs/tags/{object_id_or_tag_or_branch}"):
        with open(f"{GIT_DIR}/refs/tags/{object_id_or_tag_or_branch}", "rb") as f:
            object_id = f.read().decode()
    else:
        print("Unkown revision")
        return

    restore_tree(object_id, commit=True)
    set_ref(object_id, "heads", get_current_branch())


def get_tags():
    with os.scandir(f"{GIT_DIR}/refs/tags") as it:
        return [file.name for file in it]


def create_tag(tag):
    existing = get_ref("tags", tag)
    if existing:
        print("Tag already exists")
    else:
        head = get_ref("heads", get_current_branch())
        set_ref(head, "tags", tag)


def log(object_id):
    if object_id:
        try:
            head = get_object(object_id, "commit")
        except FileNotFoundError:
            print("fatal: unknown revision not in the working tree.")
            raise SystemExit(1)

    else:
        head = get_ref("heads", get_current_branch())

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


def commit(msg, user, time):
    tree = write_tree()
    commit_content = f"tree {tree}\n"

    parent = get_ref("heads", get_current_branch())
    # TODO: move this out to a 'working_tree_is_clean' function
    if parent is not None:
        parent_tree = get_object(parent, "commit").split("\n")[0].split(" ")[1]
        if parent_tree == tree:
            return "Nothing to commit, working tree clean"
        commit_content += f"parent {parent}\n"

    commit_content += f"author {user}\n" + f"time {time}\n\n" + msg
    revision = hash_object(commit_content.encode(), "commit")
    set_ref(revision, "heads", get_current_branch())
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
