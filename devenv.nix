{ pkgs, ... }:

{
  packages = [ 
    pkgs.zlib
    pkgs.libz
  ];
  languages.python.enable = true;
  languages.python.version = "3.11.6";
  languages.python.venv.enable = true;
  languages.python.venv.requirements = "moviepy \n pytest \n openai-whisper ";
}
