import argparse
import datetime
import os

import internal


def parse_args():
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest="command")
    commands.required = True

    init_parser = commands.add_parser("init")
    init_parser.set_defaults(func=init)

    hash_object_parser = commands.add_parser("hash-object")
    hash_object_parser.set_defaults(func=hash_object)
    hash_object_parser.add_argument("file")

    cat_file_parser = commands.add_parser("cat-file")
    cat_file_parser.set_defaults(func=cat_file)
    cat_file_parser.add_argument("object_id")

    write_tree_parser = commands.add_parser("write-tree")
    write_tree_parser.set_defaults(func=write_tree)

    restore_tree_parser = commands.add_parser("restore-tree")
    restore_tree_parser.set_defaults(func=restore_tree)
    restore_tree_parser.add_argument("object_id")

    commit_parser = commands.add_parser("commit")
    commit_parser.set_defaults(func=commit)
    commit_parser.add_argument("-m", "--message", required=False)

    log_parser = commands.add_parser("log")
    log_parser.set_defaults(func=log)
    log_parser.add_argument("object_id", nargs="?")

    checkout_parser = commands.add_parser("checkout")
    checkout_parser.set_defaults(func=checkout)
    checkout_parser.add_argument("object_id"),
    checkout_parser.add_argument(
        "-b", "--branch", action=argparse.BooleanOptionalAction
    )

    tag_parser = commands.add_parser("tag")
    tag_parser.set_defaults(func=tag)
    tag_parser.add_argument("-a", "--add", required=False)

    status_parser = commands.add_parser("status")
    status_parser.set_defaults(func=status)

    return parser.parse_args()


def status(_):
    internal.status()


def tag(args):
    if args.add:
        internal.create_tag(args.add)
    else:
        tags = internal.get_tags()
        for tag in tags:
            print(tag)


def checkout(args):
    if args.branch:
        internal.branch_out(args.object_id)
        return
    internal.checkout(args.object_id)


def log(args):
    internal.log(args.object_id)


def commit(args):
    if not args.message:
        with open(internal.COMMIT_MSG_PATH, "w") as f:
            info = (
                "\n# Please enter the commit message for your changes. Lines starting\n"
                + "# with '#' will be ignored, and an empty message aborts the commit."
                + f"\n#\n# On branch '{internal.get_HEAD()}'"
            )
            f.write(info)
        os.system(f"vi {internal.COMMIT_MSG_PATH}")
        args.message = open(internal.COMMIT_MSG_PATH, "r").read()

    datetime_string = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(internal.commit(args.message, os.environ["USER"], datetime_string))


def write_tree(_):
    print(internal.write_tree())


def restore_tree(args):
    internal.restore_tree(args.object_id)


def init(_):
    internal.init()
    print(f"Initialized empty pygit repository in {os.getcwd()}/{internal.GIT_DIR}")


def cat_file(args, expected_type="blob"):
    content = internal.get_object(args.object_id, expected_type)
    print(content)


def hash_object(args):
    with open(args.file, "rb") as f:
        data = f.read()
        object_id = internal.hash_object(data, "blob")
        print(object_id)


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
