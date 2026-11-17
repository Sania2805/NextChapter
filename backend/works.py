"""Conservative edition grouping for the catalog's title and author metadata."""

import re
import unicodedata
from html import unescape


def normalize(value):
    value = unicodedata.normalize("NFKD", unescape(value).casefold().replace("&", " and "))
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"['’‘ʼ]", "", value)
    return " ".join(re.findall(r"[^\W_]+", value))


# Strip only recognized presentation labels. Keep substantive subtitles, volume
# numbers, guides, adaptations, and collections as part of a work's identity.
EDITION_LABEL = re.compile(
    r"(?:a novel|a romance|a memoir|a thriller|large print|(?:random house )?large print edition"
    r"|random house large print|paperback|hardcover|mass market paperback"
    r"|audio(?:book| book| cd| cassette)?|audio editions mystery masters"
    r"|unabridged|unabridged audio(?: cd)?"
    r"|(?:spanish|english|french|german|italian|latin|irish gaelic|urdu|welsh)(?: language)? edition|revised edition|illustrated edition|\d+(?:st|nd|rd|th) anniversary edition"
    r"|oprahs book club(?: paperback| hardcover)?|bestselling backlist"
    r"|everymans library|cover to cover|(?:penguin |signet |modern library )"
    r"(?:modern |twentieth century |english )?classics(?: s)?(?: paperback| hardcover)?)"
)
TRAILING_GROUP = re.compile(r"\s*(\((?:[^()]|\([^()]*\))*\)|\[[^\[\]]*\])\s*\.?$")
TRAILING_SUBTITLE = re.compile(r"\s*(?::|\s[–—-]\s)\s*([^:]+)$")


def base_title(title):
    title = title.strip()
    while match := TRAILING_GROUP.search(title) or TRAILING_SUBTITLE.search(title):
        if not EDITION_LABEL.fullmatch(normalize(match[1])):
            break
        title = title[:match.start()].rstrip()
    return normalize(title)


# Catalog entries with known alternate titles. Scope aliases to the credited
# author and the entire normalized title, so matching a fragment never merges a work.
ALIAS_GROUPS = {
    "agathachristie": (
        ("and then there were none", "and then there were none e"),
    ),
    "georgeorwell": (
        ("1984", "nineteen eighty four", "neunzehnhundertvierundachtzig"),
    ),
    "danbrown": (
        ("the da vinci code", "el codigo da vinci", "el codigo da vinci the da vinci code"),
    ),
    "jkrowling": (
        ("harry potter and the sorcerers stone", "harry potter and the philosophers stone",
         "harry potter y la piedra filosofal", "harry potter und der stein der weisen",
         "harry potter a lecole des sorciers",
         "harrius potter et philosophi lapis harry potter and the philosophers stone latin edition",
         "harri potter maen yr athronydd harry potter and the philosophers stone welsh edition"),
        ("harry potter and the chamber of secrets", "harry potter y la camara secreta",
         "harry potter und die kammer des schreckens", "harry potter et la chambre des secrets"),
        ("harry potter and the prisoner of azkaban", "harry potter y el prisionero de azkaban",
         "harry potter und der gefangene von azkaban", "harry potter et le prisonnier dazkaban"),
        ("harry potter and the goblet of fire", "harry potter y el caliz de fuego",
         "harry potter und der feuerkelch"),
        ("harry potter and the order of the phoenix",),
    ),
}
ALIASES = {
    (author, title): group[0]
    for author, groups in ALIAS_GROUPS.items()
    for group in groups
    for title in group
}
ROWLING_LABEL = re.compile(
    r" (?:book [1-7](?: audio(?: cd)?| large print)?|harry potter(?: paperback| hardcover)?)$"
)

# The catalog credits the illustrator for the reinforced binding and credits
# Orwell for a Monarch Notes study guide written by Ralph A. Ranald.
AUTHOR_CORRECTIONS = {
    "0606170979": "J. K. Rowling",
    "067100719X": "Ralph A. Ranald",
}


def identify_work(isbn, title, author):
    author_key = normalize(AUTHOR_CORRECTIONS.get(isbn, author)).replace(" ", "")
    if author_key == "joannekrowling":
        author_key = "jkrowling"
    # This verified German edition has a damaged title string in the CSV.
    if isbn == "3548256279" and author_key == "georgeorwell":
        return (author_key, "1984")
    title_key = base_title(title)
    if not title_key or not author_key or author_key in {"unknown", "anonymous", "na"}:
        return ("isbn", isbn)
    if author_key == "jkrowling":
        unlabelled = ROWLING_LABEL.sub("", title_key)
        if (author_key, unlabelled) in ALIASES:
            title_key = unlabelled
    return (author_key, ALIASES.get((author_key, title_key), title_key))



