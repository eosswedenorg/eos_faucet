# eos_faucet

# install eos_faucet
## get code from github
```
git clone https://github.com/zsq978663747/eos_faucet.git
```
## start keosd

## create wallet and faucetaccout
```
cleos wallet create -n eosfaucetwallet

cleos system newaccount eosio eosfaucet1111  <public-key> <public-key> --stake-net "10 EOS" --stake-cpu "10 EOS" --buy-ram "5 EOS"
```
import eosfaucet1111 private-key to eosfaucetwallet.wallet
```
cleos wallet import -n eosfaucetwallet --private-key <private-key>
```
## set the wallet.py config
open wallet.py, paste account (to create account, transfer tokens) name, wallet name, wallet password accordingly, then save
,such as:
```
ACCOUNT = "eosfaucet111"

# paste your local wallet name
NAME = "eosfaucetwallet"

# paste your local wallet password
PASSWD = "PW5xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

```

## start server
```
python clfaucet.py
```


# client side:

you can create at most 1000 accounts per day. 
```
curl http://your_server_ip/create_account?<new_account_name>
```

you can get 100 tokens each call and max 1000 tokens per day. 
```
curl http://your_server_ip/get_token?<your_account_name>
```
## note:

this code is for test purpose only, you should not use it on eos mainnet with your real account
