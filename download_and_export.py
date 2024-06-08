import asyncio
import logging
import os
import subprocess
import sys
import json

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger("")

books = json.load(open("books.json", "r"))


def convert_cookies_to_json():
    with open(".cookies", "r") as f:
        COOKIE = f.readlines()[0]

    cookie_dict = dict((part.strip().split("=", 1) for part in COOKIE.split(";")))
    json.dump(cookie_dict, open("cookies.json", "w"))


def escape_dirname(dirname, clean_space=False):
    if ":" in dirname:
        if dirname.index(":") > 15:
            dirname = dirname.split(":")[0]

        elif "win" in sys.platform:
            dirname = dirname.replace(":", ",")

    for ch in [
        "~",
        "#",
        "%",
        "&",
        "*",
        "{",
        "}",
        "\\",
        "<",
        ">",
        "?",
        "/",
        "`",
        "'",
        '"',
        "|",
        "+",
        ":",
    ]:
        if ch in dirname:
            dirname = dirname.replace(ch, "_")

    return dirname if not clean_space else dirname.replace(" ", "")


def clean_book_title(book_id):
    book_title = books[book_id]
    return "".join(escape_dirname(book_title).split(",")[:2]) + " ({0})".format(book_id)


def book_path(book_id):
    return f"Books/{clean_book_title(book_id)}"


def book_repr(book_id):
    return f"{books[book_id]}({book_id})"


def calibre_library_path(book_id):
    rel_path = f"~/Calibre Library/{clean_book_title(book_id)}.epub"
    return os.path.expanduser(rel_path)


async def downdload_book(book_id):
    if os.path.exists(book_path(book_id)):
        logger.info(
            f'[Downloader-{book_id}] Book "{book_repr(book_id)}" already downloaded at "{book_path(book_id)}", skipped downloading'
        )
        return

    logger.info(f'[Downloader-{book_id}] Downloading book "{book_repr(book_id)}"...')
    process = await asyncio.create_subprocess_exec(
        *["python", "safaribooks.py", book_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, error = await process.communicate()
    returncode = await process.wait()
    if returncode:
        logger.error(
            f'[Downloader-{book_id}] Downloading book "{book_repr(book_id)}" got error: (Code: {returncode}, Output: {output}), Error: {error})'
        )
    else:
        logger.info(
            f'[Downloader-{book_id}] Dowloaded book "{book_repr(book_id)}" sucessfully to path "{book_path(book_id)}"'
        )


async def convert_book(book_id):
    if not os.path.exists(book_path(book_id)):
        logger.error(
            f'[Converter-{book_id}] Book "{book_repr(book_id)}" is not downloaded at path "{book_path(book_id)}", skip converting'
        )
        return

    if os.path.exists(calibre_library_path(book_id)):
        logger.info(
            f'[Converter-{book_id}] Book "{book_repr(book_id)}" is already converted at path "{calibre_library_path(book_id)}", skip converting'
        )
        return

    logger.info(f'[Converter-{book_id}] Converting book "{book_repr(book_id)}"...')
    process = await asyncio.create_subprocess_exec(
        *[
            "ebook-convert",
            f"{book_path(book_id)}/{book_id}.epub",
            calibre_library_path(book_id),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output, error = await process.communicate()
    returncode = await process.wait()
    if returncode:
        logger.error(
            f'[Converter-{book_id}] Converting book "{book_repr(book_id)}" got error: (Code: {returncode}, Output: {output}), Error: {error})'
        )
    else:
        logger.info(
            f'[Converter-{book_id}] Convreted book "{book_repr(book_id)}" sucessfully to path "{calibre_library_path(book_id)}"'
        )


async def chain(book_id):
    await downdload_book(book_id)
    await convert_book(book_id)


async def main():
    convert_cookies_to_json()

    tasks = []
    for book_id in books:
        task = asyncio.create_task(chain(book_id))
        tasks.append(task)

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
