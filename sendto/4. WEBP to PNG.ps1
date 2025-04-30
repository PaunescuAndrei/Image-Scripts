$python = "python"
$script = "E:\Wallpapers\scripts\convertwebp.py"
$customArgs = "-gtmp", "-d"
$argumentsString = ($args | ForEach-Object { '"' + $_ + '"' }) -join ' '
$arguments = $customArgs + $argumentsString

Start-Process -NoNewWindow -FilePath $python -ArgumentList @($script +" "+ $arguments)






