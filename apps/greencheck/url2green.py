import csv
import re


# these files are large, and we need to read from one file,
# and only write the lines that count as real hostnames
# we can check the host


def lazy_messy_url_list(path_to_infile):
    """
    Accept a text file at `path`, with one url per line,
    and return an generator to iterate through each line
    """
    with open(path, "r") as messy_list_of_urls:
        for line in messy_list_of_urls.readlines():
            yield line


def write_clean_urls(lazy_url_list, path_to_outfile):
    """
    Accept `lazy_url_list`, a iterable list of urls and
    write the valid urls to the file `path_to_outfile`
    """
    with open(path_to_outfile, "w") as clean_url_list:
        for url in lazy_url_iterator:
            if is_valid_hostname(url):
                clean_url_list.write(url)

def is_valid_hostname(hostname):
    """
    Check that hostname passed in is valid.
    Pretty much a copy paste of this
    https://stackoverflow.com/questions/2532053/validate-a-hostname-string
    """
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))

# Usage
# urls = lazy_messy_url_list("path/to/file")
# write_clean_urls(urls)