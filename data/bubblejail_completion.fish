# Disable file completion
complete --command bubblejail --no-files
# Completion function
function bubblejail_complete_func
    bubblejail list --command-line (commandline --cut-at-cursor) _auto_complete 
end

complete --command bubblejail --arguments '(bubblejail_complete_func)'
