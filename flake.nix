{
  description = "Cookbook overlay";

  outputs = inputs: {
    overlay = final: prev: {
      cartograph = final.callPackage ./derivation.nix {};
    };
  };
}
