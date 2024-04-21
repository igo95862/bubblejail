#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862
_complete_bubblejail()
{
	local IFS=$'\t\n'    # normalize IFS
	local PYTHON_RETURN=$(bubblejail auto-complete "${COMP_LINE::$COMP_POINT}" )
	COMPREPLY=( $(compgen -W "$PYTHON_RETURN" -- "$2") )
}

complete -F _complete_bubblejail bubblejail
