# Disable file completion
complete --command bubblejail --no-files
# Completion function
function bubblejail_complete_func
    bubblejail auto-complete (commandline --cut-at-cursor)
end

complete --command bubblejail --arguments '(bubblejail_complete_func)'
