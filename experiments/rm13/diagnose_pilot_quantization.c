#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <math.h>
#include <glob.h>
#include <sys/stat.h>
typedef struct { char magic[8]; uint32_t version,bits,group_size,groups; int64_t k,m; uint64_t fingerprint; } Header;
static uint64_t fnv(const void* p,size_t n){const unsigned char*b=p;uint64_t h=UINT64_C(14695981039346656037);for(size_t i=0;i<n;i++){h^=b[i];h*=UINT64_C(1099511628211);}return h;}
static int32_t round_even(float x){return (int32_t)nearbyintf(x);}
static int readall(const char*p,void*x,size_t n){FILE*f=fopen(p,"rb");if(!f)return 0;int ok=fread(x,1,n,f)==n;fclose(f);return ok;}
static int decode(int8_t q){return q;}
static void histogram(const char*dir){glob_t g={0};char pat[1024];snprintf(pat,sizeof(pat),"%s/*_w4_g128.bin",dir);if(glob(pat,0,NULL,&g)){puts("HIST_FAIL glob");return;}uint64_t hist[15]={0},total=0,files=0;for(size_t f=0;f<g.gl_pathc;f++){FILE*fp=fopen(g.gl_pathv[f],"rb");Header h;if(!fp||fread(&h,sizeof h,1,fp)!=1){if(fp)fclose(fp);continue;}if(memcmp(h.magic,"RM13WQ1",7)||h.bits!=4||h.group_size!=128){fclose(fp);continue;}fseek(fp,(long)((size_t)h.m*h.groups*sizeof(float)),SEEK_CUR);size_t cb=(size_t)h.m*h.groups*64;unsigned char*c=malloc(cb);if(!c||fread(c,1,cb,fp)!=cb){free(c);fclose(fp);continue;}fclose(fp);files++;for(int64_t r=0;r<h.m;r++)for(uint32_t gr=0;gr<h.groups;gr++){int valid=(int)fmin(128.0,(double)h.k-(double)gr*128.0);size_t off=((size_t)r*h.groups+gr)*64;for(int i=0;i<valid;i++){int q=(c[off+i/2]>>((i&1)*4))&15;if(q&8)q-=16;hist[q+7]++;total++;}}free(c);}uint64_t sat=hist[0]+hist[14];printf("HIST files=%" PRIu64 " elements=%" PRIu64 " q-7..7=",files,total);for(int i=0;i<15;i++)printf("%s%" PRIu64,i?",":"",hist[i]);printf(" sat=%" PRIu64 " sat_fraction=%.9g\n",sat,(double)sat/(double)total);globfree(&g);}
static int diag_up0(const char*cache,const char*raw){
    char p[1024];Header h;FILE*f=fopen(cache,"rb");if(!f||fread(&h,sizeof h,1,f)!=1){puts("DIAG_FAIL cache read");return 0;}if(memcmp(h.magic,"RM13WQ1",7)||h.bits!=4||h.k!=1152||h.m!=4304||h.groups!=9){puts("DIAG_FAIL cache header");fclose(f);return 0;}float*ws=malloc((size_t)h.m*h.groups*sizeof(float));size_t cb=(size_t)h.m*h.groups*64;unsigned char*codes=malloc(cb);if(!ws||!codes||fread(ws,sizeof(float),(size_t)h.m*h.groups,f)!=(size_t)h.m*h.groups||fread(codes,1,cb,f)!=cb){puts("DIAG_FAIL cache payload");fclose(f);free(ws);free(codes);return 0;}fclose(f);
    snprintf(p,sizeof(p),"%s/ffn_up-0.weight.f16",raw);_Float16*w=malloc((size_t)h.k*h.m*sizeof(_Float16));if(!w||!readall(p,w,(size_t)h.k*h.m*sizeof(_Float16))){puts("DIAG_FAIL weight");return 0;}if(fnv(w,(size_t)h.k*h.m*sizeof(_Float16))!=h.fingerprint){puts("DIAG_FAIL source fingerprint mismatch");return 0;}
    snprintf(p,sizeof(p),"%s/ffn_up-0.activation.f32",raw);float*x=malloc((size_t)h.k*sizeof(float));if(!x||!readall(p,x,(size_t)h.k*sizeof(float))){puts("DIAG_FAIL activation");return 0;}
    snprintf(p,sizeof(p),"%s/ffn_up-0.output.f32",raw);float*y0=malloc((size_t)h.m*sizeof(float));if(!y0||!readall(p,y0,(size_t)h.m*sizeof(float))){puts("DIAG_FAIL original output");return 0;}
    int8_t*xq=malloc((size_t)h.k);float xs[9];for(int gr=0;gr<9;gr++){int start=gr*128,valid=(int)fmin(128.0,(double)h.k-start);float mx=0;for(int i=0;i<valid;i++)if(fabsf(x[start+i])>mx)mx=fabsf(x[start+i]);xs[gr]=mx?mx/127.0f:1.0f;for(int i=0;i<valid;i++){int q=round_even(x[start+i]/xs[gr]);if(q < -127)q=-127;if(q>127)q=127;xq[start+i]=(int8_t)q;}}
    double ss=0,rr=0,oo=0,dot=0,mx=0;uint64_t hist[15]={0},sat=0;
    for(int64_t r=0;r<h.m;r++){volatile float y=0;for(int gr=0;gr<9;gr++){int start=gr*128,valid=(int)fmin(128.0,(double)h.k-start);int32_t sum=0;size_t off=((size_t)r*9+gr)*64;for(int i=0;i<valid;i++){int q=(codes[off+i/2]>>((i&1)*4))&15;if(q&8)q-=16;hist[q+7]++;if(q==-7||q==7)sat++;sum+=q*(int32_t)xq[start+i];}volatile float term=(float)sum;term=term*ws[(size_t)r*9+gr];term=term*xs[gr];y=y+term;}double a=y,b=y0[r],d=a-b;if(fabs(d)>mx)mx=fabs(d);ss+=d*d;rr+=b*b;oo+=a*a;dot+=a*b;}
    printf("DIAG qid=37804 op=ffn_up-0 layer=0 W4A8 K=1152 M=4304 sampled_tokens=1 reference=RM11_original_capture source_fingerprint=match maxabs=%.9g rmse=%.9g cosine=%.15g\n",mx,sqrt(ss/h.m),sqrt(rr*oo)==0?1:dot/sqrt(rr*oo));printf("LAYER_HIST elements=%" PRIu64 " q-7..7=",(uint64_t)h.k*h.m);for(int i=0;i<15;i++)printf("%s%" PRIu64,i?",":"",hist[i]);printf(" saturated=%" PRIu64 " fraction=%.9g\n",sat,(double)sat/((double)h.k*h.m));free(ws);free(codes);free(w);free(x);free(y0);free(xq);return 1;
}
int main(int argc,char**argv){if(argc!=3){fprintf(stderr,"usage: %s W4_CACHE_DIR RM11_TENSOR_DIR\n",argv[0]);return 2;}char cache[1024];snprintf(cache,sizeof(cache),"%s/ffn_up-0_w4_g128.bin",argv[1]);histogram(argv[1]);return diag_up0(cache,argv[2])?0:1;}
