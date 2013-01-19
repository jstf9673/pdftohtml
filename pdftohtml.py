import subprocess
import os
#from BeautifulSoup import BeautifulSoup


def log(data):
    f = open('/tmp/pdftohtml.log', 'a')
    f.write(str(data))


class Text(str):
    """holds string-the atomic element of book.
       wraps the str type to escape the html elements automaticaly
    """
    __slots__ = []

    def __new__(cls, string,):
        replace_dict = {'<': '&lt;', '>': '&gt;', '"': '&quot;'}
        for key, val in replace_dict.iteritems():
            string = string.replace(key, val)
        return super(Text, cls).__new__(cls, string)


class Lines(list):
    """holds lines of book"""
    def __init__(self, txtdata=''):
        txtdata = self.preConditionData(txtdata)
        lines = [Text(line) for line in txtdata.splitlines()]
        list.__init__(self, lines)
        self.linelen = self.computeAvglineLen(txtdata)

    def initFromlist(self, linelist, linelen):
        """alternate way to initialize this class' object"""
        list.__init__(self, linelist)
        self.linelen = linelen
        return self

    def preConditionData(self, txtdata):
        """conditions txt by removing unnecessary lines
        """
        txtdata = txtdata.replace('\n\n', '\n')
        txtdata = txtdata.replace('\x0c\x0c', '\x0c')
        return txtdata

    def sanitize(self):
        """remove running headers and lines representing
           only page number
        """
        #TODO: remove running headers,pgno lines
        sanitized = self[:1]
        pagebreakflag = False
        for line in self[1:]:
            if line.startswith('\x0c'):
                if sanitized[-1].isdigit():
                    sanitized.pop(-1)
                if len(line) < self.linelen:
                    pagebreakflag = True
                else:
                    sanitized.append(line)
            else:
                if pagebreakflag:
                        line = '\x0c' + line
                        pagebreakflag = False
                sanitized.append(line)
        return Lines().initFromlist(sanitized, self.linelen)

    def computeAvglineLen(self, txtdata):
        if txtdata:
            return int(len(txtdata) / len(self))
        return 0


class Paragraph(list):
    """holds paragraph in sequence"""
    levelmap = [1000, 0.6, 0.7, 0.8, 0.9, 1]

    def __init__(self, lines, level=1):
        self.level = self.levelmap[int(level)]
        paras = self.linesTopara(lines)
        list.__init__(self, paras)

    def linesTopara(self, lines):
        paras = []
        para = lines[0]
        for i in range(1, len(lines)):
            if self.isparabreak(lines[i], lines[i - 1], lines.linelen):
                paras.append(para)
                para = ''
            para += '\n' + lines[i]
        return paras

    def isparabreak(self, currentline, prevline, linelen):
        if currentline[0] == '\x0c':
            currentline = currentline[1:]
        if currentline[0].islower():
            return False
        if prevline[-1].islower():
            return False
        if currentline.startswith(('‘', "'")):
            if prevline.endswith(('’', "'")):
                return True
        if currentline.startswith(('“', '"')):
            if prevline.endswith(('”', '"')):
                return True
        if len(prevline) < int(linelen * self.level):
            if prevline.endswith(('.', '!', '?', '”', '"', '’', "'")):
                if currentline.startswith(('‘', '“', "'", '"')):
                    return True
                if currentline[0].isupper():
                    return True
        return False


class PDFtohtml(object):
    """
    """
    def __init__(self):
        self.lastexception = ''

    def verifyContext(self, in_location, out_location, context_object):
        return True, ''

    def getLastException(self):
        return str(self.lastexception)

    def process(self, in_location, out_location, context_object):
        filename = os.path.split(in_location)[1]
        txtfile = out_location + os.sep + filename.rsplit('.')[0] + '.txt'
        htmlfile = out_location + os.sep + filename.rsplit('.')[0] + '.html'
        PDFtohtml.pdftotxt(in_location, txtfile)
        PDFtohtml.txttoHtml(txtfile, htmlfile,
                            context_object['pgmap'], context_object['level'])
        return True, ''

    @staticmethod
    def invoke(args):
        P = subprocess.PIPE
        p = subprocess.Popen(
            args, stdin=P, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_, stderr_ = p.communicate()
        if stderr_:
            raise Exception(stderr_)
        return stdout_

    @staticmethod
    def pdftotxt(pdf_path, txt_path):
        args = ['pdftotext', '-enc', 'UTF-8', pdf_path, txt_path]
        return PDFtohtml.invoke(args)

    @staticmethod
    def txttoHtml(txtfile, htmlfile, pgmap, level):
        # sets the intensity of paragraphing
        lines = Lines(open(txtfile).read())
        lines = lines.sanitize()
        paras = Paragraph(lines, level)  # holds list of paras
        # generate fx output
        book = '<p>' + '</p><p>'.join(paras) + '</p>'
        pageseqno = 1
        while book.find('\x0c') != -1:
            retval = PDFtohtml.pgmapLookup(pageseqno, pgmap)
            if retval:
                pageno = retval
            else:
                pageno = int(pageno) + 1
            book = book.replace('\x0c',
             '<span  class="pagebreak-rw">{0}</span>'.format(pageno), 1)
            pageseqno += 1

        lastpgno = 0
        for pageseq, realpageno, section in pgmap:
            if lastpgno == 0:
                book = section + book
                lastpgno = realpageno
                continue
            searchstr = '<span  class="pagebreak-rw">{0}</span>'.format(
                                                                    lastpgno)
            book = book.replace(searchstr, searchstr + '</div>' + section)
            lastpgno = realpageno
        book += '</div>'
        book = book.replace('\n', '<br/>')
        book = book.replace('<br/></p>', '</p>')
        book = book.replace('<p><br/>', '<p>')
        book = book.replace('<br/>', ' <br />\n')
        book = book.replace('</p>', '</p>\n')
#        book = BeautifulSoup(book).prettify()
        T = '<html>\n <head>\n  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n \n </head>\n \n <body>\n  {0}\n </body>\n</html>'
        book = T.format(book)
        f = open(htmlfile, 'w')
        f.write(book)
        f.close()

    @staticmethod
    def pgmapLookup(pagesqno, pgmap):
        """lookup page no and section break in pgmap"""
        for pageseq, realpgno, section in pgmap:
            if int(pageseq) == pagesqno:
                return realpgno
        return False


if __name__ == '__main__':
    pdf = '/home/infogrid/Desktop/skypefiles/pdftohtml/PDF2HTMLSimpleTestTrimmed.pdf'
    pgmap = [(1, 'i', '<div class=\xe2\x80\x9dfrontmatter-rw BookTitlePage-rw\xe2\x80\x9d>'),
            (2, 'ii', '<div class=\xe2\x80\x9dfrontmatter-rw Copyright-rw\xe2\x80\x9d>'),
            (3, 'iii', '<div class=\xe2\x80\x9dfrontmatter-rw Preface-rw\xe2\x80\x9d>'),
            (4, '1', '<div class=\xe2\x80\x9dbody-rw Chapter-rw\xe2\x80\x9d>')]

    print PDFtohtml().process(pdf, '/tmp', {'pgmap':pgmap, 'level':0})
