{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    poetry
    (pkgs.callPackage ./derivation.nix {})
  ];
}
