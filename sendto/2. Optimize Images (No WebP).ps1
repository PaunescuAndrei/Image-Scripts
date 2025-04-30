$python = "python"
$script = "E:\Wallpapers\scripts\pingopy.py"
$customArgs = "-gtmp", "-s", "4", "-nt", "2", "-nowebp"
$argumentsString = ($args | ForEach-Object { '"' + $_ + '"' }) -join ' '
$arguments = $customArgs + $argumentsString

Start-Process -NoNewWindow -FilePath $python -ArgumentList @($script +" "+ $arguments)






