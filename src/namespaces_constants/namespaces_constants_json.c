// SPDX-License-Identifier: GPL-3.0-or-later
/* Copyright 2019-2022 igo95862
 *
 * This file is part of bubblejail.
 * bubblejail is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * bubblejail is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * You should have received a copy of the GNU General Public License
 * along with bubblejail.  If not, see <https://www.gnu.org/licenses/>.
 */
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
