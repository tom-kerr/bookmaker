#include <stdio.h>
#include <stdlib.h>

int main() {

  int *p1, *p2, *n;
  n = (int*)malloc(sizeof(int)*5);
  n[0] = 5;
  p1 = &n[0];
  p2 = p1;
  p2 = NULL;
  printf("p1 is ..p2 is %d\n", *p1);
  //free(&p2);

}
