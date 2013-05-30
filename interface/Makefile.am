AUTOMAKE_OPTIONS = nostdinc

dist_pkgpython_PYTHON = isl.py isl_core.py
noinst_PROGRAMS = extract_interface

AM_CXXFLAGS = $(CLANG_CXXFLAGS)
AM_LDFLAGS = $(CLANG_LDFLAGS)

INCLUDES = -I$(top_builddir) -I$(top_srcdir) \
	-I$(top_builddir)/include -I$(top_srcdir)/include

extract_interface_SOURCES = \
	python.h \
	python.cc \
	extract_interface.h \
	extract_interface.cc
extract_interface_LDADD = \
	-lclangFrontend -lclangSerialization -lclangParse -lclangSema \
	$(LIB_CLANG_EDIT) \
	-lclangAnalysis -lclangAST -lclangLex -lclangBasic -lclangDriver \
	$(CLANG_LIBS) $(CLANG_LDFLAGS)

isl_core.py: extract_interface isl.py.top
	(cat $(srcdir)/isl.py.top; \
		./extract_interface$(EXEEXT) $(INCLUDES) $(srcdir)/all.h) \
			> isl_core.py

TESTS_ENVIRONMENT = LD_LIBRARY_PATH=$(top_builddir)/.libs PYTHONPATH=. $(PYTHON)
check_SCRIPTS = isl_core.py
TESTS = isl.py
