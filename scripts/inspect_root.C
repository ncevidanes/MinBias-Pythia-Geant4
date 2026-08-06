#include <TFile.h>
#include <TTree.h>

#include <iostream>

void inspect_root(const char* filename = "outputs/minbias_smoke.root") {
  TFile file(filename, "READ");
  if (file.IsZombie()) {
    std::cerr << "Não foi possível abrir: " << filename << '\n';
    return;
  }

  for (const char* name : {"events", "hits", "generator"}) {
    auto* tree = file.Get<TTree>(name);
    if (!tree) {
      std::cout << name << ": ausente\n";
      continue;
    }
    std::cout << name << ": " << tree->GetEntries() << " entradas\n";
    tree->Print();
  }
}

