AC_INIT([isl], [0.12], [isl-development@googlegroups.com])
AC_CONFIG_AUX_DIR([.])
AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE([foreign])
m4_ifdef([AM_SILENT_RULES],[AM_SILENT_RULES([yes])])
AC_SUBST(versioninfo)
versioninfo=12:0:2

if test "x$prefix" != "xNONE"; then
	prefix_wd=`cd $prefix && pwd`
	srcdir_wd=`cd $srcdir && pwd`
	wd=`pwd`
	if test "x$prefix_wd" = "x$srcdir_wd"; then
		AC_MSG_ERROR(Installation in source directory not supported)
	fi
	if test "x$prefix_wd" = "x$wd"; then
		AC_MSG_ERROR(Installation in build directory not supported)
	fi
fi

AC_PROG_CC
AC_PROG_CXX

AX_CC_MAXOPT
AX_GCC_WARN_UNUSED_RESULT
AX_C___ATTRIBUTE__

AC_PROG_LIBTOOL

AC_CHECK_PROG(PERL, perl, perl, [])
AC_CHECK_PROG(PDFLATEX, pdflatex, pdflatex, [])
AC_CHECK_PROG(POD2HTML, pod2html, pod2html, [])

AM_CONDITIONAL(GENERATE_DOC, test -n "$PERL" -a -n "$PDFLATEX" -a -n "$POD2HTML")

AX_CREATE_STDINT_H(include/isl/stdint.h)

AX_SUBMODULE(gmp,system|build,system)

AC_SUBST(GMP_CPPFLAGS)
AC_SUBST(GMP_LDFLAGS)
AC_SUBST(GMP_LIBS)
case "$with_gmp" in
system)
	if test "x$with_gmp_prefix" != "x"; then
		isl_configure_args="$isl_configure_args --with-gmp=$with_gmp_prefix"
		GMP_CPPFLAGS="-I$with_gmp_prefix/include"
		GMP_LDFLAGS="-L$with_gmp_prefix/lib"
	fi
	GMP_LIBS=-lgmp
	SAVE_CPPFLAGS="$CPPFLAGS"
	SAVE_LDFLAGS="$LDFLAGS"
	SAVE_LIBS="$LIBS"
	CPPFLAGS="$GMP_CPPFLAGS $CPPFLAGS"
	LDFLAGS="$GMP_LDFLAGS $LDFLAGS"
	LIBS="$GMP_LIBS $LIBS"
	AC_CHECK_HEADER([gmp.h], [], [AC_ERROR([gmp.h header not found])])
	AC_CHECK_LIB([gmp], [main], [], [AC_ERROR([gmp library not found])])
	AC_LINK_IFELSE([AC_LANG_PROGRAM([[#include <gmp.h>]], [[
		mpz_t n, d;
		if (mpz_divisible_p(n, d))
			mpz_divexact_ui(n, n, 4);
	]])], [], [AC_ERROR([gmp library too old])])
	CPPFLAGS="$SAVE_CPPFLAGS"
	LDFLAGS="$SAVE_LDFLAGS"
	LIBS="$SAVE_LIBS"
	;;
build)
	GMP_CPPFLAGS="-I$gmp_srcdir -I$with_gmp_builddir"
	GMP_LIBS="$with_gmp_builddir/libgmp.la"
	;;
esac
SAVE_CPPFLAGS="$CPPFLAGS"
SAVE_LDFLAGS="$LDFLAGS"
SAVE_LIBS="$LIBS"
CPPFLAGS="$GMP_CPPFLAGS $CPPFLAGS"
LDFLAGS="$GMP_LDFLAGS $LDFLAGS"
LIBS="$GMP_LIBS $LIBS"
need_get_memory_functions=false
AC_CHECK_DECLS(mp_get_memory_functions,[],[
	need_get_memory_functions=true
],[#include <gmp.h>])
AC_RUN_IFELSE([AC_LANG_PROGRAM([[#include <gmp.h>]], [[
	mpz_t x,y,g,a,b;
	mpz_init(x);
	mpz_init(y);
	mpz_init(g);
	mpz_init(a);
	mpz_init(b);
	mpz_set_si(x, -1);
	mpz_set_si(y, 9);
	mpz_gcdext(g, a, b, x, y);
	if (mpz_get_si(a) == -1 && mpz_get_si(b) == 0)
		return 0;
	else
		return 1;
]])], [need_normalized_gcdext=false], [need_normalized_gcdext=true],
[need_normalized_gcdext=true])
CPPFLAGS="$SAVE_CPPFLAGS"
LDFLAGS="$SAVE_LDFLAGS"
LIBS="$SAVE_LIBS"
AM_CONDITIONAL(NEED_GET_MEMORY_FUNCTIONS, test x$need_get_memory_functions = xtrue)
if test $need_normalized_gcdext = true; then
AC_DEFINE([GMP_NORMALIZE_GCDEXT], [],
	[result of mpz_gcdext needs to be normalized])
fi

AC_SUBST(CLANG_CXXFLAGS)
AC_SUBST(CLANG_LDFLAGS)
AC_SUBST(CLANG_LIBS)
AX_SUBMODULE(clang,system|no,no)
case "$with_clang" in
system)
	llvm_config="llvm-config"
	AC_CHECK_PROG([llvm_config_found], ["$llvm_config"], [yes])
	if test "x$with_clang_prefix" != "x"; then
		llvm_config="$with_clang_prefix/bin/llvm-config"
		if test -x "$llvm_config"; then
			llvm_config_found=yes
		fi
	fi
	if test "$llvm_config_found" != yes; then
		AC_MSG_ERROR([llvm-config not found])
	fi
	CLANG_CXXFLAGS=`$llvm_config --cxxflags`
	CLANG_LDFLAGS=`$llvm_config --ldflags`
	targets=`$llvm_config --targets-built`
	CLANG_LIBS=`$llvm_config --libs $targets asmparser bitreader support mc`
	CLANG_PREFIX=`$llvm_config --prefix`
	AC_DEFINE_UNQUOTED(CLANG_PREFIX, ["$CLANG_PREFIX"],
				[Clang installation prefix])

	SAVE_CPPFLAGS="$CPPFLAGS"
	CPPFLAGS="$CLANG_CXXFLAGS $CPPFLAGS"
	AC_LANG_PUSH(C++)
	AC_CHECK_HEADER([clang/Basic/SourceLocation.h], [],
		[AC_ERROR([clang header file not found])])
	AC_EGREP_HEADER([getDefaultTargetTriple], [llvm/Support/Host.h], [],
		[AC_DEFINE([getDefaultTargetTriple], [getHostTriple],
		[Define to getHostTriple for older versions of clang])])
	AC_EGREP_HEADER([getExpansionLineNumber],
		[clang/Basic/SourceLocation.h], [],
		[AC_DEFINE([getExpansionLineNumber],
			[getInstantiationLineNumber],
	    [Define to getInstantiationLineNumber for older versions of clang])])
	AC_EGREP_HEADER([DiagnosticsEngine],
		[clang/Basic/Diagnostic.h], [],
		[AC_DEFINE([DiagnosticsEngine],
			[Diagnostic],
	    [Define to Diagnostic for older versions of clang])])
	AC_EGREP_HEADER([ArrayRef], [clang/Driver/Driver.h],
		[AC_DEFINE([USE_ARRAYREF], [],
			[Define if Driver::BuildCompilation takes ArrayRef])])
	AC_EGREP_HEADER([CXXIsProduction], [clang/Driver/Driver.h],
		[AC_DEFINE([HAVE_CXXISPRODUCTION], [],
		[Define if Driver constructor takes CXXIsProduction argument])])
	AC_EGREP_HEADER([ IsProduction], [clang/Driver/Driver.h],
		[AC_DEFINE([HAVE_ISPRODUCTION], [],
		[Define if Driver constructor takes IsProduction argument])])
	AC_EGREP_HEADER([void HandleTopLevelDecl\(], [clang/AST/ASTConsumer.h],
		[AC_DEFINE([HandleTopLevelDeclReturn], [void],
			   [Return type of HandleTopLevelDeclReturn])
		 AC_DEFINE([HandleTopLevelDeclContinue], [],
			   [Return type of HandleTopLevelDeclReturn])],
		[AC_DEFINE([HandleTopLevelDeclReturn], [bool],
			   [Return type of HandleTopLevelDeclReturn])
		 AC_DEFINE([HandleTopLevelDeclContinue], [true],
			   [Return type of HandleTopLevelDeclReturn])])
	AC_CHECK_HEADER([clang/Basic/DiagnosticOptions.h],
		[AC_DEFINE([HAVE_BASIC_DIAGNOSTICOPTIONS_H], [],
			   [Define if clang/Basic/DiagnosticOptions.h exists])])
	AC_TRY_COMPILE([#include <clang/Basic/TargetInfo.h>], [
		using namespace clang;
		TargetOptions *TO;
		DiagnosticsEngine *Diags;
		TargetInfo::CreateTargetInfo(*Diags, TO);
	], [AC_DEFINE([CREATETARGETINFO_TAKES_POINTER], [],
		      [Define if TargetInfo::CreateTargetInfo takes pointer])])
	AC_TRY_COMPILE([#include <clang/Frontend/CompilerInstance.h>], [
		using namespace clang;
		DiagnosticConsumer *client;
		CompilerInstance *Clang;
		Clang->createDiagnostics(client);
	], [], [AC_DEFINE([CREATEDIAGNOSTICS_TAKES_ARG], [],
	[Define if CompilerInstance::createDiagnostics takes argc and argv])])
	AC_TRY_COMPILE([#include <clang/Lex/HeaderSearchOptions.h>], [
		using namespace clang;
		HeaderSearchOptions HSO;
		HSO.AddPath("", frontend::Angled, false, false);
	], [AC_DEFINE([ADDPATH_TAKES_4_ARGUMENTS], [],
		[Define if HeaderSearchOptions::AddPath takes 4 arguments])])
	AC_LANG_POP
	CPPFLAGS="$SAVE_CPPFLAGS"

	SAVE_LDFLAGS="$LDFLAGS"
	LDFLAGS="$CLANG_LDFLAGS $LDFLAGS"
	AC_SUBST(LIB_CLANG_EDIT)
	AC_CHECK_LIB([clangEdit], [main], [LIB_CLANG_EDIT=-lclangEdit], [])
	LDFLAGS="$SAVE_LDFLAGS"
	;;
esac
AM_CONDITIONAL(HAVE_CLANG, test $with_clang = system)

AX_SET_WARNING_FLAGS

AC_SUBST(WARNING_FLAGS)

PACKAGE_CFLAGS="$GMP_CPPFLAGS"
PACKAGE_LDFLAGS="$GMP_LDFLAGS"
PACKAGE_LIBS="-lisl -lgmp"
AX_CREATE_PKGCONFIG_INFO

AX_DETECT_GIT_HEAD
echo '#define GIT_HEAD_ID "'$GIT_HEAD_ID'"' > gitversion.h

AH_BOTTOM([#include <isl_config_post.h>])
AC_CONFIG_HEADERS(isl_config.h)
AC_CONFIG_HEADERS(include/isl/config.h)
AC_CONFIG_FILES(Makefile)
AC_CONFIG_FILES(doc/Makefile)
if test $with_clang = system; then
	AC_CONFIG_FILES(interface/Makefile)
fi
AC_CONFIG_FILES([bound_test.sh], [chmod +x bound_test.sh])
AC_CONFIG_FILES([codegen_test.sh], [chmod +x codegen_test.sh])
AC_CONFIG_FILES([pip_test.sh], [chmod +x pip_test.sh])
AC_CONFIG_COMMANDS_POST([
	dnl pass on arguments to subdir configures, but don't
	dnl add them to config.status
	ac_configure_args="$ac_configure_args $isl_configure_args"
])
AC_OUTPUT
