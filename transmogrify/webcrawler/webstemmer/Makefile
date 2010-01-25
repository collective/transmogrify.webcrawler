# Makefile

VERSION=0.6.1
GTAR=tar
DESTDIR=/tmp/please/specify/the/directory
HTMLDIR=$$HOME/public_html/python/webstemmer/

FILES=Makefile \
	README.txt \
	analyze.py \
	extract.py \
	htmldom.py \
	sgmlparser3.py \
	htmlparser3.py \
	htmlutils.py \
	httplib.py \
	zipdb.py \
	layoutils.py \
	urldbutils.py \
	html2txt.py \
	textcrawler.py \
	style.py \
	perf.py

all:

clean:
	-rm *.pyc *.pyo *~

pack: clean
	ln -s webstemmer ../webstemmer-$(VERSION)
	cd ..; $(GTAR) c -z --dereference -f webstemmer-$(VERSION).tar.gz webstemmer-$(VERSION) \
		--exclude OLD --exclude '*.obj'
	rm ../webstemmer-$(VERSION)

install: clean
	[ -d $(DESTDIR) ] && cp $(FILES) $(DESTDIR)

install-doc:
	cp docs/*.png docs/*.html $(HTMLDIR)
