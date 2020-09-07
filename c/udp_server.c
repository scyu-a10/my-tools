#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <sys/errno.h>
#include <string.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <pthread.h>
#include <unistd.h>
int SERV_PORT=101;

#define MAXNAME 65535

/* Compile:
 * gcc udp_server.c -lpthread -o udp_server  
 */

extern int errno;
long byte_count=0;
long packet_count=0;
long ret_packet_count=0;
pthread_t thread1, thread2;

void *thread(void *ptr)
{
    int num=0;
    long prev_count=0;
    long count_diff=0;
    while (1) {
        count_diff = packet_count - prev_count;
        if( count_diff ){
            printf("%d:packet count=%ld, total reply=%ld\n", num, count_diff, ret_packet_count);
        }
        prev_count = packet_count;
        num++;
        sleep(1);
    }
}

int main(int argc, char *argv[]) {
    int socket_fd;   /* file description into transport */
    int recfd; /* file descriptor to accept        */
    int length; /* length of address structure      */
    int nbytes; /* the number of read **/
    char buf[BUFSIZ];
    struct sockaddr_in myaddr; /* address of this service */
    struct sockaddr_in client_addr; /* address of client    */
    /*
     *      Get a socket into UDP/IP
     */
    if (argc ==2) {
        int port ;
        port = atoi(argv[1]);
        SERV_PORT = port;
    }
    printf("listen on port %d\n",SERV_PORT);
    if ((socket_fd = socket(AF_INET, SOCK_DGRAM, 0)) <0) {
        perror ("socket failed");
        exit(EXIT_FAILURE);
    }
    /*
     *    Set up our address
     */
    bzero ((char *)&myaddr, sizeof(myaddr));
    myaddr.sin_family = AF_INET;
    myaddr.sin_addr.s_addr = htonl(INADDR_ANY);
    myaddr.sin_port = htons(SERV_PORT);

    /*const char *intf = "ens19.200";
    if (setsockopt(socket_fd, SOL_SOCKET, SO_BINDTODEVICE, intf, strnlen(intf, IFNAMSIZ)) < 0) {
        perror("bind intf error");
        exit(1);
    }*/

    /*
     *     Bind to the address to which the service will be offered
     */
    if (bind(socket_fd, (struct sockaddr *)&myaddr, sizeof(myaddr)) <0) {
        perror ("bind failed\n");
        exit(1);
    }

    /*
     * Loop continuously, waiting for datagrams
     * and response a message
     */
    length = sizeof(client_addr);
    printf("Server is ready to receive !!\n");
    printf("Can strike Ctrl-c to stop Server >>\n");

    pthread_create(&thread1, NULL, *thread, (void *) 1);

    while (1) {
        if ((nbytes = recvfrom(socket_fd, &buf, MAXNAME, 0, (struct sockaddr*)&client_addr, (socklen_t *)&length)) <0) {
            perror ("could not read datagram!!");
            continue;
        }
        byte_count += nbytes;
        packet_count ++;

        //printf("Received data form %s : %d\n", inet_ntoa(client_addr.sin_addr), htons(client_addr.sin_port));
        //printf("%s\n", buf);

        /* return to client */
        if (sendto(socket_fd, &buf, nbytes, 0, (struct sockaddr*)&client_addr, length) < 0) {
            perror("Could not send datagram!!\n");
            continue;
        } 
        ret_packet_count++;
        //printf("Can Strike Crtl-c to stop Server >>\n");
    }
    printf("byte_count=%ld\n",byte_count);
    printf("packet_count=%ld\n",packet_count);
    return 0;
}
