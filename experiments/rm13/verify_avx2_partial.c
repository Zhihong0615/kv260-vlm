#include <immintrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static int32_t avx_partial(const uint8_t *w, const int8_t *x, int bits, int valid) {
    __m256i acc = _mm256_setzero_si256();
    const __m128i mask = _mm_set1_epi8(0x0f), sign = _mm_set1_epi8(0x08);
    for (int k=0; k<valid; k+=16) {
        __m128i w8;
        if (bits==8) w8=_mm_loadu_si128((const __m128i *)(w+k));
        else {
            size_t off=(size_t)k/2;
            __m128i p=_mm_loadl_epi64((const __m128i *)(w+off));
            __m128i lo=_mm_and_si128(p,mask);
            __m128i hi=_mm_and_si128(_mm_srli_epi16(p,4),mask);
            w8=_mm_unpacklo_epi8(lo,hi);
            w8=_mm_sub_epi8(_mm_xor_si128(w8,sign),sign);
        }
        __m128i x8=_mm_loadu_si128((const __m128i *)(x+k));
        __m256i w16=_mm256_cvtepi8_epi16(w8), x16=_mm256_cvtepi8_epi16(x8);
        acc=_mm256_add_epi32(acc,_mm256_madd_epi16(w16,x16));
    }
    int32_t lanes[8], out=0; _mm256_storeu_si256((__m256i *)lanes,acc);
    for(int i=0;i<8;i++) out+=lanes[i];
    return out;
}
static int32_t scalar_partial(const uint8_t *w,const int8_t*x,int bits,int valid){
    int32_t s=0;
    for(int k=0;k<valid;k++){
        int32_t q;
        if(bits==8) q=(int8_t)w[k];
        else { uint8_t n=(w[k/2]>>((k&1)*4))&15; q=(n&8)?(int)n-16:n; }
        s+=q*(int32_t)x[k];
    }
    return s;
}
static uint32_t rng=0x13a56b7c; static uint32_t next(void){rng^=rng<<13;rng^=rng>>17;rng^=rng<<5;return rng;}
static int check_group(int bits,int valid){
    uint8_t w4[64]={0},w8[128]={0}; int8_t x[128];
    for(int i=0;i<valid;i++){
        int qx=(int)(next()%255)-127; int qw=bits==4?(int)(next()%15)-7:(int)(next()%255)-127;
        if(i==0){qx=-127;qw=bits==4?-7:-127;} if(i==1){qx=127;qw=bits==4?7:127;}
        x[i]=(int8_t)qx;
        if(bits==4) w4[i/2]|=(uint8_t)((qw&15)<<((i&1)*4)); else w8[i]=(uint8_t)(int8_t)qw;
    }
    uint8_t *w=bits==4?w4:w8; int32_t a=avx_partial(w,x,bits,valid),b=scalar_partial(w,x,bits,valid);
    if(a!=b){fprintf(stderr,"random mismatch bits=%d valid=%d avx=%d scalar=%d\n",bits,valid,a,b);return 0;} return 1;
}
static int32_t round_even(float x){return (int32_t)nearbyintf(x);}
static int check_real(void){
    const char *base="/home/zhiro/research/kv260-vlm-workers/RM11-A-unified/experiments/rm11_unified_ffn/evidence/host_capture/tensors/ffn_up-0";
    char wp[512],xp[512]; snprintf(wp,sizeof(wp),"%s.weight.f16",base);snprintf(xp,sizeof(xp),"%s.activation.f32",base);
    FILE *wf=fopen(wp,"rb"),*xf=fopen(xp,"rb"); if(!wf||!xf){perror("real tensor open");return 0;}
    _Float16 w[1152]; float x[1152];
    int ok=fread(w,sizeof(w[0]),1152,wf)==1152 && fread(x,sizeof(x[0]),1152,xf)==1152; fclose(wf);fclose(xf); if(!ok){fprintf(stderr,"short real tensor read\n");return 0;}
    int8_t xq[1152]; float xs[9]; uint8_t w4[9*64]={0},w8[1152]; float ws4[9],ws8[9];
    for(int g=0;g<9;g++){
        float xmax=0,wmax=0; int start=g*128,valid=1152-start<128?1152-start:128;
        for(int i=0;i<valid;i++){float xv=x[start+i],wv=(float)w[start+i];if(fabsf(xv)>xmax)xmax=fabsf(xv);if(fabsf(wv)>wmax)wmax=fabsf(wv);}
        xs[g]=xmax?xmax/127.0f:1.0f;ws4[g]=wmax?wmax/7.0f:1.0f;ws8[g]=wmax?wmax/127.0f:1.0f;
        for(int i=0;i<valid;i++){
            xq[start+i]=(int8_t)round_even(x[start+i]/xs[g]);
            int q4=round_even((float)w[start+i]/ws4[g]);if(q4 < -7)q4=-7;if(q4>7)q4=7;
            int q8=round_even((float)w[start+i]/ws8[g]);if(q8 < -127)q8=-127;if(q8>127)q8=127;
            w4[g*64+i/2]|=(uint8_t)((q4&15)<<((i&1)*4)); w8[start+i]=(uint8_t)(int8_t)q8;
        }
        int a4=avx_partial(w4+g*64,xq+start,4,valid),b4=scalar_partial(w4+g*64,xq+start,4,valid);
        int a8=avx_partial(w8+start,xq+start,8,valid),b8=scalar_partial(w8+start,xq+start,8,valid);
        if(a4!=b4||a8!=b8){fprintf(stderr,"real mismatch g=%d valid=%d W4 %d/%d W8 %d/%d\n",g,valid,a4,b4,a8,b8);return 0;}
    }
    printf("REAL_OK ffn_up-0 token0 K=1152 groups=9 W4+W8 AVX2 partials equal independent scalar partials\n"); return 1;
}
int main(void){
    if(!check_group(4,128)||!check_group(8,128)||!check_group(4,80)||!check_group(8,80))return 1;
    puts("RANDOM_OK W4/W8 K=128 and tail=80 include signed extrema");
    return check_real()?0:1;
}
