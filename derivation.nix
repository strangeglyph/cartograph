{ lib, pkgs, ... }:

pkgs.python3Packages.buildPythonPackage rec {
    pname = "cartograph";
    version = "0.1.0";
    src = ./.;

    propagatedBuildInputs = with pkgs.python3Packages; [ flask ];

    pythonImportsCheck = [ "flask" ];
    doCheck = false;

    postInstall = ''
        cp -r cartograph/static $out/static
        echo "from cartograph import app" > $out/wsgi.py
    '';

    meta = with lib; {
        homepage = "https://github.com/strangeglyph/cartograph";
        description = "Hiking tracker";
        license = licenses.mit;
    };
}
