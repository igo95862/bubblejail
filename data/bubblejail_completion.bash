#/usr/bin/env bash

_complete_bubblejail()
{
	local IFS=$'\t\n'    # normalize IFS
	local PYTHON_RETURN=$(bubblejail _auto_complete "$COMP_LINE" "$COMP_CWORD")
	COMPREPLY=( $(compgen -W "$PYTHON_RETURN" -- "$2") )
}

complete -F _complete_bubblejail bubblejail
