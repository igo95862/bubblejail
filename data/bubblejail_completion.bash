#/usr/bin/env bash

_complete_bubblejail()
{
	local IFS=$'\t\n'    # normalize IFS
	local PYTHON_RETURN=$(bubblejail list --command-line "${COMP_LINE::$COMP_POINT}"  _auto_complete)
	COMPREPLY=( $(compgen -W "$PYTHON_RETURN" -- "$2") )
}

complete -F _complete_bubblejail bubblejail
