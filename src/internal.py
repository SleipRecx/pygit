import hashlib
import os

GIT_DIR = ".pygit"
DEFAULT_BRANCH_NAME = "main"
COMMIT_MSG_PATH = f"{GIT_DIR}/COMMIT_EDITMSG"

# Used for DEV mode, such that no source code is
# lost by running pygit locally with bugs.
CURRENT_DIR = "testing"


def create_dir_if_not_exists(path):
    try:
        os.makedirs(path)
        return True
    except FileExistsError:
        return False


def init():
    create_dir_if_not_exists(GIT_DIR)
    create_dir_if_not_exists(f"{GIT_DIR}/objects")
    create_dir_if_not_exists(f"{GIT_DIR}/refs")
    create_dir_if_not_exists(f"{GIT_DIR}/refs/heads")
    create_dir_if_not_exists(f"{GIT_DIR}/refs/tags")

    try:
        with open(f"{GIT_DIR}/HEAD", "x") as f:
            f.write(DEFAULT_BRANCH_NAME)
    except FileExistsError:
        pass

    try:
        # Needs correct permissions
        open(f"{GIT_DIR}/COMMIT_EDITMSG", "x").close()
    except FileExistsError:
        pass


def head_is_detached():
    with open(f"{GIT_DIR}/HEAD", "rb") as f:
        object_id_or_branch_name = f.read().decode()
        return os.path.exists(f"{GIT_DIR}/objects/{object_id_or_branch_name}")


def get_ignored():
    with open(".pygitignore", "r") as f:
        return set(row for row in f.read().split("\n") if not row.startswith("#"))


def status():
    with open(f"{GIT_DIR}/HEAD", "rb") as f:
        object_id_or_branch_name = f.read().decode()

    if head_is_detached():
        print(f"HEAD detached at {object_id_or_branch_name}")
        return

    msg = f"On branch '{object_id_or_branch_name}'\n"

    if is_working_tree_clean():
        msg += "nothing to commit, working tree clean"
    else:
        msg += "there are changes staged for commit"

    print(msg)


def get_HEAD():
    with open(f"{GIT_DIR}/HEAD", "rb") as f:
        object_id_or_branch_name = f.read().decode()
        if head_is_detached():
            return object_id_or_branch_name

        branch_object_id = get_ref("heads", object_id_or_branch_name)
        return branch_object_id


def get_current_branch_name():
    with open(f"{GIT_DIR}/HEAD", "rb") as f:
        return f.read().decode()


def set_HEAD(object_id_or_branch_name):
    with open(f"{GIT_DIR}/HEAD", "w") as f:
        f.write(object_id_or_branch_name)


def get_ref(ref_type, name):
    if not os.path.exists(f"{GIT_DIR}/refs/{ref_type}/{name}"):
        return None
    with open(f"{GIT_DIR}/refs/{ref_type}/{name}", "rb") as f:
        return f.read().decode()


def set_ref(object_id, ref_type, name):
    with open(f"{GIT_DIR}/refs/{ref_type}/{name}", "wb") as f:
        f.write(object_id.encode())


def branch_out(name):
    object_id = get_ref("heads", name)
    if object_id:
        print(f"Branch '{name}' already exists.")
        return

    HEAD = get_HEAD()
    set_ref(HEAD, "heads", name)
    set_HEAD(name)


def checkout(object_id_or_tag_or_branch):
    if os.path.exists(f"{GIT_DIR}/objects/{object_id_or_tag_or_branch}"):
        object_id = object_id_or_tag_or_branch
        set_HEAD(object_id)
    elif os.path.exists(f"{GIT_DIR}/refs/heads/{object_id_or_tag_or_branch}"):
        with open(f"{GIT_DIR}/refs/heads/{object_id_or_tag_or_branch}", "rb") as f:
            object_id = f.read().decode()
            set_HEAD(object_id_or_tag_or_branch)
    elif os.path.exists(f"{GIT_DIR}/refs/tags/{object_id_or_tag_or_branch}"):
        with open(f"{GIT_DIR}/refs/tags/{object_id_or_tag_or_branch}", "rb") as f:
            object_id = f.read().decode()
            set_HEAD(object_id)
    else:
        print(f"Unkown revision '{object_id_or_tag_or_branch}'")
        return

    restore_tree(object_id, commit=True)


def get_tags():
    with os.scandir(f"{GIT_DIR}/refs/tags") as it:
        return [file.name for file in it]


def create_tag(tag):
    existing = get_ref("tags", tag)
    if existing:
        print("Tag already exists")
    else:
        HEAD = get_HEAD()
        set_ref(HEAD, "tags", tag)


def log(object_id):
    if object_id:
        try:
            get_object(object_id, "commit")
        except FileNotFoundError:
            print("fatal: unknown revision not in the working tree.")
            raise SystemExit(1)

    else:
        object_id = get_HEAD()

    if object_id is None:
        print("No commits exists yet.")
        return

    current = object_id
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


def is_working_tree_clean():
    tree = write_tree()
    parent = get_HEAD()
    if parent is not None:
        parent_tree = get_object(parent, "commit").split("\n")[0].split(" ")[1]
        if parent_tree == tree:
            return True
        return False

    return False


def commit(msg, user, time):
    if head_is_detached():
        print("Commit on detached HEAD is not supported.")
        return

    if is_working_tree_clean():
        print("Nothing to commit, working tree clean")
        return

    parent = get_HEAD()
    tree = write_tree()

    commit_content = f"tree {tree}\n"

    if parent:
        commit_content += f"parent {parent}\n"

    # Strip out comments from commit msg
    msg = "\n".join([line for line in msg.split("\n") if not line.startswith("#")])

    commit_content += f"author {user}\n" + f"time {time}\n\n" + msg

    revision = hash_object(commit_content.encode(), "commit")

    if not parent:
        set_HEAD(DEFAULT_BRANCH_NAME)
        set_ref(revision, "heads", DEFAULT_BRANCH_NAME)
    else:
        branch_name = get_current_branch_name()
        set_ref(revision, "heads", branch_name)

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
