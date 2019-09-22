<?php
namespace sammo\img_service;

include(__DIR__.'/HashKey.php');

function hashPassword($salt, $password)
{
    return hash('sha512', $salt.$password.$salt);
}


function getVersion($target=null){
    if($target){
        $command = sprintf('git describe %s --long --tags', escapeshellarg($target));
    }
    else{
        $command = 'git describe --long --tags';
    }
    exec($command, $output);
    if(is_array($output)){
        $output = join('', $output);
    }
    return trim($output);
    
}

header('Content-Type: application/json');

$req_hash = $_REQUEST['req']??'';
$req_time = $_REQUEST['time']??0;

$json_response = [
    'result'=>false,
    'reason'=>'Unknown',
    'version'=>null,
];

if(!$req_hash){
    $json_response['reason'] = 'no req';
    die(json_encode($json_response));
}
if(!$req_time || !is_numeric($req_time)){
    $json_response['reason'] = 'invalid time';
    die(json_encode($json_response));
}

$key = HashKey::KEY;
if(strlen($key)<16){
    $json_response['reason'] = 'key is too short';
    die(json_encode($json_response));
}

$timestamp = time();

if(abs($timestamp - $req_time) > 300){
    $json_response['reason'] = 'time difference';
    die(json_encode($json_response));
}

$ans_hash = hashPassword(sprintf("%016x", $req_time), $key);

if($ans_hash != $req_hash){
    $json_response['reason'] = 'hash mismatch';
    die(json_encode($json_response));
}

exec("git pull -q 2>&1", $output);

exec("git ls-files -z ../icons", $raw_img_list);
$raw_img_list = explode("\x00", $raw_img_list[0]);
$img_list = [];

foreach ($raw_img_list as $path) {
    $pos = strpos($path, '../icons/');
    if($pos === false){
        continue;
    }
    $path = substr($path, $pos + 9);


    $pathinfo = pathinfo($path);
    $dpath = $pathinfo['dirname'];
    $basename = $pathinfo['basename'];
    $filename = $pathinfo['filename'];

    if(!\key_exists($dpath, $img_list)){
        $img_list[$dpath] = [];
    }
    $img_list[$dpath][$filename] = $basename;

}

file_put_contents('list.json', json_encode($img_list));



$json_response['result'] = true;
$json_response['reason'] = 'success';
$json_response['version'] = getVersion();
die(json_encode($json_response));