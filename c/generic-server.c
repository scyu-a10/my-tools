#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <getopt.h>
#include <unistd.h>

#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/errno.h>
#include <net/if.h>
#include <arpa/inet.h>

struct running_config_t {
    unsigned char 
        use_v4: 1,
        use_udp: 1,
        spare: 6;
    unsigned short port;
};

int get_sockfd(struct running_config_t *conf);

int main(int argc, char *argv[])
{
    int ch = 0, opt_idx = 0;
    int sockfd;
    struct running_config_t conf;
    conf.use_v4 = 1;
    conf.use_udp = 1; 
    conf.port = 5000;
    
    /* parse user arguement:
     * - default is udp + ipv4.
     */
    struct option long_opt[] = 
    {
        {"use-v6", no_argument, NULL, '6'},
        {"tcp", no_argument, NULL, '2'},
        {"port", required_argument, NULL, 'p'},
        {0, 0, 0, 0}
    };

    while((ch = getopt_long_only(argc, argv, "26p:", long_opt, &opt_idx)) != -1) {
        switch (ch) {
            case '2': {
                conf.use_udp = 0;
                break;
            }
            case '6': {
                conf.use_v4 = 0;
                break;
            }
            case 'p': {
                if (optarg) {
                    unsigned int raw = atoi(optarg);
                    if (raw < 65535){
                        conf.port = raw;
                    } else {
                        conf.port = raw % 65535;
                    }
                }
                break;
            }
            default: 
                /* unsupport */
                break;
        }
    }
    
    puts("===================================================");
    printf("L3 protocol: %s\n", conf.use_v4 ? "IPv4": "IPv6");
    printf("L4 protocol: %s\n", conf.use_udp ? "UDP": "TCP");
    printf(" - Listening on port: %d\n", conf.port);
    puts("===================================================");

    sockfd = get_sockfd(&conf);

    /* handle requests from client */
    char buff[BUFSIZ];
    int length, nbytes;
    struct sockaddr_in client;
    struct sockaddr_in6 client6;

    length = sizeof(client);
    puts("Server is ready to receive.");
    puts("Use Ctrl-c to stop Server >>");

    if (!conf.use_udp) {
        int backlog = 5; /* maximum connection == 5 */
        listen(sockfd, backlog); 
        accept(sockfd, NULL, NULL);
    }

    while(1) {
        if ((nbytes = recvfrom(sockfd, &buff, BUFSIZ, 0, (struct sockaddr*)&client, (socklen_t *)&length)) < 0) {
            perror("could not read datagram!");
            continue;
        }
    }

    close(sockfd);

    return 0;
}

int get_sockfd(struct running_config_t *conf)
{
    int sockfd;
    short port = conf->port, sin_family;
    struct sockaddr_in server_addr;
    struct sockaddr_in6 server_addr6;

    bzero((char *)&server_addr, sizeof(server_addr));
    bzero((char *)&server_addr6, sizeof(server_addr6));

    if (conf->use_v4) {
        // ipv4 
        if (conf->use_udp) {
            // udp
            if ((sockfd = socket(AF_INET, SOCK_DGRAM, 0)) < 0) {
                perror("create ipv4/udp socket failed");
                exit(EXIT_FAILURE);
            }
        } else {
            // tcp
            if ((sockfd = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
                perror("create ipv4/tcp socket failed");
                exit(EXIT_FAILURE);
            }
        }

        server_addr.sin_family = AF_INET;
        server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
        server_addr.sin_port = htons(port);
        if (bind(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
            perror("bind failed\n");
            exit(EXIT_FAILURE);
        }
    } else {
        // ipv6
        if (conf->use_udp) {
            // udp
            if ((sockfd = socket(AF_INET6, SOCK_DGRAM, 0)) < 0) {
                perror("create ipv6/udp socket failed");
                exit(EXIT_FAILURE);
            }
        } else {
            // tcp
            if ((sockfd = socket(AF_INET6, SOCK_STREAM, 0)) < 0) {
                perror("create ipv6/tcp socket failed");
                exit(EXIT_FAILURE);
            }
        }

        server_addr6.sin6_family = AF_INET6;
        server_addr6.sin6_addr = in6addr_any;
        server_addr6.sin6_port = htons(port);
        if (bind(sockfd, (struct sockaddr *)&server_addr6, sizeof(server_addr6)) < 0) {
            perror("bind v6 failed\n");
            exit(EXIT_FAILURE);
        }
    }

    return sockfd;
}
