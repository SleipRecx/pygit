import argparse
import datetime
import os

import internal

GIT_DIR = ".pygit"


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
    commit_parser.add_argument("-m", "--message", required=True)

    return parser.parse_args()


def commit(args):
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
