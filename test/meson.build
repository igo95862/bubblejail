unittests = files(
    'test_helper.py',
    'test_profiles.py',
    'test_service_info.py',
    'test_auto_completion.py',
)

foreach unittest : unittests
    test(
        fs.stem(unittest),
        py_installation,
        args : [unittest],
        env : test_env,
    )
endforeach
