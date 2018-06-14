<?php

namespace sammo\img_service;

include(__DIR__.'/gogs_key.php');

$raw_payload = $_POST['payload']??'false';
$valid_hmac = $_SERVER['HTTP_X_GOGS_SIGNATURE']??'';
$req_hmac = hash_hmac('sha256', $raw_payload, Key::KEY);

if($valid_hmac != $req_hmac){
    die('');
}

exec("git pull -q 2>&1", $output);