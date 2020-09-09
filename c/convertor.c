#include <arpa/inet.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <ctype.h>

int main(int argc, char *argv[])
{
    if (argc < 3) {
        printf("Usage: ./convertor [ntohs|ntohl|htons|htonl] <number>\n");
        printf("\nFor example:\n");
        printf("bash-4.2$ ./convertor ntohs 50195\nntohs(50195) = 5060\n\n");
        return -1;
    }

    if (!strcmp(argv[1], "ntohs")) { // network to host short
        if (argv[2][1] == 'x') {
            int before_convert = strtol(argv[2], NULL, 16);
            printf("ntohs(0x%x) = 0x%x\n", before_convert, ntohs(before_convert));
        } else {
            int before_convert = atoi(argv[2]);
            printf("ntohs(%d) = %d\n", before_convert, ntohs(before_convert));
        }
    } 
    else if (!strcmp(argv[1], "htons")) { // host to network short
        if (argv[2][1] == 'x') {
            int before_convert = strtol(argv[2], NULL, 16);
            printf("htons(0x%x) = 0x%x\n", before_convert, htons(before_convert));
        } else {
            int before_convert = atoi(argv[2]);
            printf("htons(%d) = %d\n", before_convert, htons(before_convert));
        }
    }
    else if (!strcmp(argv[1], "ntohl")) { // network to host long (u32)
        if (argv[2][1] == 'x') {
            int before_convert = strtol(argv[2], NULL, 16);
            printf("ntohl(0x%x) = 0x%x\n", before_convert, ntohl(before_convert));
        } else {
            int before_convert = atoi(argv[2]);
            printf("ntohl(%d) = %d\n", before_convert, ntohl(before_convert));
        }
    }
    else if (!strcmp(argv[1], "htonl")) { // host to network long (u32)
        if (argv[2][1] == 'x') {
            int before_convert = strtol(argv[2], NULL, 16);
            printf("htonl(0x%x) = 0x%x\n", before_convert, htonl(before_convert));
        } else {
            int before_convert = atoi(argv[2]);
            printf("htonl(%d) = %d\n", before_convert, htonl(before_convert));
        }
    }

    return 0;
}
