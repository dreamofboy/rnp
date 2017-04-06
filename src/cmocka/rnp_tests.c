#include <stdarg.h>
#include <stddef.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#include <cmocka.h>

#include <crypto.h>
#include <mj.h>

// returns new string containing hex value
char* hex_encode(const uint8_t v[], size_t len)
{
   char* s;
   size_t i;

   s = malloc(2*len + 1);
   if(s == NULL)
      return NULL;

   char hex_chars[] = "0123456789ABCDEF";

   for (i = 0; i < len; ++i)
   {
      uint8_t b0 = 0x0F & (v[i] >> 4);
      uint8_t b1 = 0x0F & (v[i]);
      const char c1 = hex_chars[b0];
      const char c2 = hex_chars[b1];
      s[2*i] = c1;
      s[2*i+1] = c2;
   }
   s[2*len] = 0;

   return s;
}

int test_value_equal(const char* what,
                     const char* expected_value,
                     const uint8_t v[], size_t v_len)
{
   char* produced = hex_encode(v, v_len);

   // fixme - expects expected_value is also uppercase
   if(strcmp(produced, expected_value) != 0)
   {
      fprintf(stderr, "Bad value for %s expected %s got %s\n", what, expected_value, produced);
      free(produced);
      return 1;
   }

   free(produced);
   return 0;
}

static void hash_test_success(void **state)
{
   pgp_hash_t hash;
   uint8_t hash_output[PGP_MAX_HASH_SIZE];

   const pgp_hash_alg_t hash_algs[] = {
      PGP_HASH_MD5,
      PGP_HASH_SHA1,
      PGP_HASH_SHA256,
      PGP_HASH_SHA384,
      PGP_HASH_SHA512,
      PGP_HASH_SHA224,
      PGP_HASH_UNKNOWN
   };

   const uint8_t test_input[3] = { 'a', 'b', 'c' };
   const char* hash_alg_expected_outputs[] = {
      "900150983CD24FB0D6963F7D28E17F72",
      "A9993E364706816ABA3E25717850C26C9CD0D89D",
      "BA7816BF8F01CFEA414140DE5DAE2223B00361A396177A9CB410FF61F20015AD",
      "CB00753F45A35E8BB5A03D699AC65007272C32AB0EDED1631A8B605A43FF5BED8086072BA1E7CC2358BAECA134C825A7",
      "DDAF35A193617ABACC417349AE20413112E6FA4E89A97EA20A9EEEE64B55D39A2192992A274FC1A836BA3C23A3FEEBBD454D4423643CE80E2A9AC94FA54CA49F",
      "23097D223405D8228642A477BDA255B32AADBCE4BDA0B3F7E36C9DA7"
   };

   for(int i = 0; hash_algs[i] != PGP_HASH_UNKNOWN; ++i)
   {
      unsigned hash_size = pgp_hash_size(hash_algs[i]);

      //printf("Testing hash # %d size %d\n", i+1, hash_size);

      assert_int_equal(hash_size*2, strlen(hash_alg_expected_outputs[i]));

      assert_int_equal(1, pgp_hash_any(&hash, hash_algs[i]));

      hash.init(&hash);
      hash.add(&hash, test_input, 1);
      hash.add(&hash, test_input + 1, sizeof(test_input) - 1);
      hash.finish(&hash, hash_output);

      test_value_equal(hash.name,
                       hash_alg_expected_outputs[i],
                       hash_output, hash_size);
   }
}

static void cipher_test_success(void **state)
{
   const uint8_t key[16] = { 0 };
   uint8_t iv[16];
   pgp_symm_alg_t alg = PGP_SA_AES_128;
   pgp_crypt_t crypt;

   uint8_t block[16] = { 0 };

   assert_int_equal(1, pgp_crypt_any(&crypt, alg));

   pgp_encrypt_init(&crypt);

   memset(iv, 0x42, sizeof(iv));

   crypt.set_crypt_key(&crypt, key);
   crypt.block_encrypt(&crypt, block, block);

   test_value_equal("AES ECB encrypt",
                    "66E94BD4EF8A2C3B884CFA59CA342B2E",
                    block, sizeof(block));

   crypt.block_decrypt(&crypt, block, block);

   test_value_equal("AES ECB decrypt",
                    "00000000000000000000000000000000",
                    block, sizeof(block));

   crypt.set_iv(&crypt, iv);
   crypt.cfb_encrypt(&crypt, block, block, 16);

   test_value_equal("AES CFB encrypt",
                    "BFDAA57CB812189713A950AD99478879",
                    block, sizeof(block));

   crypt.set_iv(&crypt, iv);
   crypt.cfb_decrypt(&crypt, block, block, 16);
   test_value_equal("AES CFB decrypt",
                    "00000000000000000000000000000000",
                    block, sizeof(block));

}
static void rsa_test_success(void **state)
{



}

int main(void) {
    const struct CMUnitTest tests[] = {
        cmocka_unit_test(hash_test_success),
        cmocka_unit_test(cipher_test_success),
        cmocka_unit_test(rsa_test_success),
    };
    return cmocka_run_group_tests(tests, NULL, NULL);
}
