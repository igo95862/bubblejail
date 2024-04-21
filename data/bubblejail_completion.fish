# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2020 igo95862

# Disable file completion
complete --command bubblejail --no-files
# Completion function
function bubblejail_complete_func
    bubblejail auto-complete (commandline --cut-at-cursor)
end

complete --command bubblejail --arguments '(bubblejail_complete_func)'
