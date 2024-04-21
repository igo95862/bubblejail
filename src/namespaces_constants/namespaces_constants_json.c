// SPDX-License-Identifier: GPL-3.0-or-later
// SPDX-FileCopyrightText: 2023 igo95862
#include <linux/nsfs.h>
#include <stdio.h>
#include <sys/syscall.h>

#define PRINT_DIGIT_CONST(NAME) fprintf(stdout, "\"" #NAME "\": %d,\n", NAME);

int main() {
        fprintf(stdout, "{\n");
        PRINT_DIGIT_CONST(__NR_setns);
        PRINT_DIGIT_CONST(NS_GET_USERNS);
        PRINT_DIGIT_CONST(NS_GET_PARENT);
        fprintf(stdout, "\"\": 0\n");  // Trailing comma
        fprintf(stdout, "}\n");
        return 0;
}
