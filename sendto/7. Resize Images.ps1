$python = "python"
$script = "D:\Wallpapers\scripts\imgmagick_resize.py"
$customArgs = "-gtmp", "-resize", "2500", "-cjpg", "0" 
$argumentsString = ($args | ForEach-Object { '"' + $_ + '"' }) -join ' '
$arguments = $customArgs + $argumentsString

Start-Process -NoNewWindow -FilePath $python -ArgumentList @($script +" "+ $arguments)






