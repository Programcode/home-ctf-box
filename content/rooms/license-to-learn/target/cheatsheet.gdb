# license-to-learn gdb cheatsheet (fill in the three @@..@@ blanks)
#
# How to use this template:
#
#   1. Work on a copy so the debugger never trips over setuid bits:
#        cp /opt/challenges/activator /tmp/activator-copy
#        chmod 755 /tmp/activator-copy
#
#   2. List the symbols you need:
#        nm /tmp/activator-copy
#      You are looking for the report function (the comparison happens
#      inside it, after the slow loop has finished) and the global
#      variable that stores the computed expectation.
#
#   3. Replace @@BREAKPOINT@@ with that function name, @@ARGUMENT@@
#      with any throwaway numeric activation code, and @@VARIABLE@@
#      with the global variable name.
#
#   4. Run it:
#        gdb -batch -x sheet.gdb /tmp/activator-copy
#      The x/1wx line dumps four bytes of memory at the global; convert
#      the printed hex to decimal and feed that back to the real binary.
set pagination off
set confirm off
break @@BREAKPOINT@@
run @@ARGUMENT@@
x/1wx &@@VARIABLE@@
