#! /usr/bin/env python
__version__ = '$Revision: 1.1 $'

import bookmarks
import errno
import getopt
import os
import string
import sys


OUTPUT_FORMATS = ("html", "xbel", "pickle", "pickle-binary")

SCRIPT_PREFIX = "bkmk2"


class Options:
    guess_type = 0
    output_format = "html"
    scrape_links = 0
    export = 0
    export_fields = []
    search = 0
    keywords = []
    __export_field_map = {
        "modified": "last_modified",
        "visited": "last_visited",
        "added": "add_date",
        }

    def __init__(self, args):
        s = os.path.splitext(os.path.basename(sys.argv[0]))
        if s[:len(SCRIPT_PREFIX)] == SCRIPT_PREFIX:
            s = s[len(SCRIPT_PREFIX):]
            if s in OUTPUT_FORMATS:
                self.output_format = s
        opts, self.args = getopt.getopt(
            sys.argv[1:], "f:ghsx",
            ["export=", "format=", "guess-type", "help", "scrape", "search="])
        for opt, arg in opts:
            if opt in ("-h", "--help"):
                usage()
            elif opt in ("-g", "--guess-type"):
                self.guess_type = 1
            elif opt in ("-f", "--format"):
                if arg not in OUTPUT_FORMATS:
                    usage(2, "unknown output format: " + arg)
                self.output_format = arg
            elif opt in ("-s", "--scrape"):
                self.scrape_links = 1
            elif opt == "-x":
                self.export = 1
            elif opt == "--export":
                self.export = 1
                fields = string.split(arg, ",")
                print fields
                for f in fields:
                    fname = self.__export_field_map[f]
                    if not fname in self.export_fields:
                        self.export_fields.append(fname)
            elif opt == "--search":
                map(self.keywords.append, string.split(arg, ","))
                self.search = 1


def main():
    try:
        options = Options(sys.argv[1:])
    except getopt.error, message:
        usage(2, message)
    args = options.args
    if options.guess_type:
        if not args:
            args = ["-"]
        for filename in args:
            guess_bookmarks_type(filename, len(args) != 1)
        return
    if len(args) > 2:
        usage(2, "too many command line arguments")
    ifn = ofn = '-'
    if args:
        ifn = args[0]
        if ifn != '-':
            base, ext = os.path.splitext(ifn)
            if sys.stdout.isatty():
                # if not a TTY, we're in a pipeline & should stick with stdout
                ofn = base + bookmarks.get_default_extension(
                    options.output_format)
    if ifn == '-':
        infile = sys.stdin
    else:
        try:
            infile = open(ifn, 'rb')    # binary in case it's a binary pickle
        except IOError, (err, message):
            if options.scrape_links:
                # try to open as URL
                import urllib
                infile = urllib.urlopen(ifn)
                if ofn != "-":
                    # we tried to guess; try again to keep it local
                    import posixpath
                    import urlparse
                    pathpart = urlparse.urlparse(ifn)[2] or '/'
                    ofn = posixpath.basename(pathpart)
                    if not ofn:
                        ofn = posixpath.basename(pathpart[:-1])
                    else:
                        ofn = posixpath.splitext(ofn)[0]
                    ofn = ofn + bookmarks.get_default_extension(
                        options.output_format)
                baseurl = infile.url
            else:
                error(1, "could not open %s: %s" % (ifn, message))
        else:
            baseurl = "file:" + os.path.join(os.getcwd(), ifn)
    if len(args) == 2:
        ofn = args[1]
    #
    # get the parser class, bypassing completely if the formats are the same
    #
    if options.scrape_links:
        import formats.html_scraper
        parser = formats.html_scraper.Parser(ifn)
        parser.set_baseurl(baseurl)
    else:
        format = bookmarks.get_format(infile)
        if not format:
            error(1, "could not identify input file format")
        parser_class = bookmarks.get_parser_class(format)
        parser = parser_class(ifn)
    #
    # do the real work
    #
    writer_class = bookmarks.get_writer_class(options.output_format)
    parser.feed(infile.read())
    parser.close()
    infile.close()
    root = parser.get_root()
    if options.search:
        import search
        import search.KeywordSearch
        search_options = search.KeywordSearch.KeywordOptions()
        search_options.set_keywords(string.join(options.keywords))
        matcher = search.get_matcher("Keyword", search_options)
        root = search.find_nodes(root, matcher)
        if root is None:
            sys.stderr.write("No matches.\n")
            sys.exit(1)
    writer = writer_class(root)
    if options.export:
        import exporter
        export_options = exporter.ExportOptions()
        for s in options.export_fields:
            setattr(export_options, "remove_" + s, 0)
        walker = exporter.ExportWalker(root, export_options)
        walker.walk()
    try:
        writer.write_tree(get_outfile(ofn))
    except IOError, (err, msg):
        # Ignore the error if we lost a pipe into another process.
        if err != errno.EPIPE:
            raise


def guess_bookmarks_type(filename, verbose=0):
    if filename == "-":
        fp = sys.stdin
    else:
        fp = open(filename)
    type = bookmarks.get_format(fp)
    if verbose:
        print "%s: %s" % (filename, type)
    else:
        print type


def get_outfile(ofn):
    if ofn == '-':
        outfile = sys.stdout
    else:
        try:
            outfile = open(ofn, 'w')
        except IOError, (errno, message):
            error(1, "could not open %s: %s" % (ofn, message))
        print "Writing output to", ofn
    return outfile


def usage(err=0, message=''):
    program = os.path.basename(sys.argv[0])
    if message:
        print "%s: %s" % (program, message)
        print
    print "usage:", program, "[infile [outfile]]"
    print
    print "\tConvert a Grail bookmarks file to an HTML bookmarks file."
    print
    print "\tIf infile is specified, the default output filename will be"
    print "\tthe name of the input file with the extension '.html'.  If both"
    print "\tinfile and outfile are omitted, input will be read from standard"
    print "\tinput and output will be written to standard output.  A hyphen"
    print "\tmay be used in either position to explicitly request the"
    print "\tcorresponding standard stream."
    sys.exit(err)


def error(err, message):
    program = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: %s\n" % (program, message))
    sys.exit(err)
