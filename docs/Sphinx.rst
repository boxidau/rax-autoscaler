What is Sphinx? 
***************

Sphinx is a tool that helps to generate python documentation. Features:

  * Output formats: HTML (including Windows HTML Help), LaTeX (for printable PDF versions), ePub, Texinfo, manual pages, plain text
  * Extensive cross-references: semantic markup and automatic links for functions, classes, citations, glossary terms and similar pieces of information
  * Hierarchical structure: easy definition of a document tree, with automatic links to siblings, parents and children
  * Automatic indices: general index as well as a language-specific module indices
  * Code handling: automatic highlighting using the Pygments highlighter


Quick start
===========

You can add inline comments about a function or class at the begining for example:

::

  def exit_with_error(msg):
      """This function prints error message and exit with error.

      :param msg: error message
      :type name: str
      :returns: 1 (int) -- the return code

      """


Execute make command in project directory with doc arg:

::

  make doc


After successful execution updated .html file sould be available here 'docs/_build/html/'



