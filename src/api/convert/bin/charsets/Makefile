SHELL = /bin/sh
INSTALL = /usr/bin/install -c

srcdir = .
top_srcdir = ..

prefix = /usr/local
installroot = 
exec_prefix = ${prefix}

bindir = ${exec_prefix}/bin
sbindir = ${exec_prefix}/sbin
libexecdir = ${exec_prefix}/libexec
datadir = ${datarootdir}
datarootdir = ${prefix}/share
sysconfdir = ${prefix}/etc
sharedstatedir = ${prefix}/com
localstatedir = ${prefix}/var
libdir = ${exec_prefix}/lib
infodir = ${datarootdir}/info
mandir = ${datarootdir}/man
includedir = ${prefix}/include
oldincludedir = /usr/include

REPL_EXT=.replchars
SPEC_EXT=.specchars
LIB_DIR=${datarootdir}/catdoc

all: cp1251.txt koi8-r.txt
clean:
install: install-dirs install-spc install-charsets
install-spc: tex.spc ascii.spc tex.rpl ascii.rpl
	    $(INSTALL) -m 644 ascii.spc $(installroot)$(LIB_DIR)/ascii$(SPEC_EXT) 
	    $(INSTALL) -m 644 tex.spc $(installroot)$(LIB_DIR)/tex$(SPEC_EXT) 
	    $(INSTALL) -m 644 ascii.rpl $(installroot)$(LIB_DIR)/ascii$(REPL_EXT)
	    $(INSTALL) -m 644 tex.rpl $(installroot)$(LIB_DIR)/tex$(REPL_EXT)
install-charsets:
	for i in *.txt; do\
	   $(INSTALL) -m 0644 $$i $(installroot)$(LIB_DIR);\
	done
install-dirs:
	../mkinstalldirs $(installroot)$(LIB_DIR)
distclean:
	rm Makefile
