"use client";

import { useRef, useState } from "react";
import {
  Upload, Sparkles, CheckCircle, XCircle, AlertTriangle, ArrowRight
} from "lucide-react";
import { predictions as predictionsApi, products as productsApi } from "@/lib/api";
import type { AnalysisResult, PredictionResult, Product } from "@/types";
import {
  formatCtr, formatCurrency, formatRoas, formatDays,
  getRecommendationColor, getRecommendationLabel,
  getScoreColor, getScoreBg, formatNarrative, formatPct
} from "@/lib/utils";
import { useEffect } from "react";
import { toast } from "sonner";

type Step = "upload" | "analyzing" | "result";

export default function CreativePredictor() {
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [headline, setHeadline] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [ctaType, setCtaType] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [step, setStep] = useState<Step>("upload");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    productsApi.list().then(setProducts);
  }, []);

  const handleFile = (f: File) => {
    setFile(f);
    const url = URL.createObjectURL(f);
    setPreview(url);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleAnalyze = async () => {
    if (!productId) {
      toast.error("Please select a product");
      return;
    }

    setStep("analyzing");

    const formData = new FormData();
    formData.append("product_id", productId);
    formData.append("headline", headline);
    formData.append("body_text", bodyText);
    formData.append("cta_type", ctaType);
    if (file) formData.append("file", file);

    try {
      const result = await predictionsApi.analyzeUpload(formData);
      setAnalysis(result.analysis);
      setPrediction(result.prediction);
      setStep("result");
    } catch (e: unknown) {
      toast.error((e as Error).message || "Analysis failed");
      setStep("upload");
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setStep("upload");
    setAnalysis(null);
    setPrediction(null);
    setHeadline("");
    setBodyText("");
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          Creative Predictor
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload a creative before launch. Get an AI prediction score, winner similarity, and recommendation.
        </p>
      </div>

      {step === "upload" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Upload Area */}
          <div className="space-y-4">
            <div
              className="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-primary/50 hover:bg-accent/30 transition-colors"
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileRef.current?.click()}
            >
              {preview ? (
                <div className="space-y-3">
                  {file?.type.startsWith("video") ? (
                    <video src={preview} className="max-h-48 mx-auto rounded-lg" controls />
                  ) : (
                    <img src={preview} alt="Preview" className="max-h-48 mx-auto rounded-lg object-contain" />
                  )}
                  <p className="text-sm text-muted-foreground">{file?.name}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-14 h-14 bg-muted rounded-xl flex items-center justify-center mx-auto">
                    <Upload className="h-7 w-7 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-medium">Drop creative here</p>
                    <p className="text-sm text-muted-foreground mt-1">Image or video · JPG, PNG, MP4, MOV</p>
                  </div>
                </div>
              )}
            </div>
            <input ref={fileRef} type="file" className="hidden" accept="image/*,video/*"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />

            {/* Ad Copy */}
            <div className="space-y-3">
              <div>
                <label className="text-sm font-medium">Headline</label>
                <input
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  placeholder="e.g., Stop hair fall in 30 days"
                  className="mt-1 w-full border border-border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Body Text</label>
                <textarea
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  rows={3}
                  placeholder="Ad body copy..."
                  className="mt-1 w-full border border-border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 resize-none"
                />
              </div>
              <div>
                <label className="text-sm font-medium">CTA Type</label>
                <input
                  value={ctaType}
                  onChange={(e) => setCtaType(e.target.value)}
                  placeholder="e.g., Shop Now, Learn More"
                  className="mt-1 w-full border border-border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>
          </div>

          {/* Config */}
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Product *</label>
              <select
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
                className="mt-1 w-full border border-border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
              >
                <option value="">Select product</option>
                {["hair", "wellness", "fitness"].map((cat) => (
                  <optgroup key={cat} label={cat.charAt(0).toUpperCase() + cat.slice(1)}>
                    {products.filter((p) => p.category === cat).map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            <div className="bg-muted/50 rounded-xl p-4 text-sm space-y-2">
              <p className="font-medium">What the AI will analyze:</p>
              {[
                "Narrative type and hook classification",
                "Similarity to historical winners and losers",
                "Narrative saturation for this product",
                "Predicted CTR, CPA, ROAS, and lifespan",
                "Fatigue risk assessment",
                "Launch recommendation",
              ].map((item) => (
                <div key={item} className="flex items-start gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                  <span className="text-muted-foreground">{item}</span>
                </div>
              ))}
            </div>

            <button
              onClick={handleAnalyze}
              disabled={!productId}
              className="w-full py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              <Sparkles className="h-4 w-4" />
              Analyze & Predict
            </button>
          </div>
        </div>
      )}

      {step === "analyzing" && (
        <div className="flex flex-col items-center justify-center py-24 gap-6">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center">
            <Sparkles className="h-8 w-8 text-primary animate-pulse-slow" />
          </div>
          <div className="text-center">
            <p className="text-lg font-semibold">Analyzing Creative...</p>
            <p className="text-sm text-muted-foreground mt-1">
              Gemini 2.5 Pro is analyzing your creative and comparing it against {" "}
              historical winners and losers.
            </p>
          </div>
          <div className="flex gap-2">
            {["Analyzing media", "Extracting attributes", "Finding similar winners", "Generating prediction"].map((s, i) => (
              <div key={s} className={`text-xs px-3 py-1 rounded-full border ${i === 0 ? "bg-primary text-primary-foreground border-primary" : "bg-muted text-muted-foreground border-border"}`}>
                {s}
              </div>
            ))}
          </div>
        </div>
      )}

      {step === "result" && prediction && analysis && (
        <div className="space-y-6">
          {/* Main Score */}
          <div className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Creative Success Score</p>
                <div className="flex items-baseline gap-2 mt-1">
                  <span className={`text-5xl font-bold ${getScoreColor(prediction.creative_success_score)}`}>
                    {prediction.creative_success_score.toFixed(0)}
                  </span>
                  <span className="text-muted-foreground text-lg">/100</span>
                </div>
                <div className="mt-3">
                  <span className={`inline-flex items-center px-3 py-1 rounded-lg text-sm font-medium border ${getRecommendationColor(prediction.recommendation)}`}>
                    {getRecommendationLabel(prediction.recommendation)}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mt-3 max-w-lg">{prediction.recommendation_reason}</p>
              </div>
              {preview && (
                <img src={preview} alt="Creative" className="w-24 h-24 rounded-xl object-cover border border-border" />
              )}
            </div>
          </div>

          {/* Score Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Narrative", score: prediction.narrative_score },
              { label: "Hook", score: prediction.hook_score },
              { label: "Visual", score: prediction.visual_score },
              { label: "Novelty", score: prediction.novelty_score },
            ].map(({ label, score }) => (
              <div key={label} className="bg-card border border-border rounded-xl p-4">
                <p className="text-sm text-muted-foreground">{label} Score</p>
                <div className="mt-2 flex items-end gap-2">
                  <span className={`text-2xl font-bold ${getScoreColor(score)}`}>{score.toFixed(0)}</span>
                  <span className="text-muted-foreground text-sm mb-0.5">/100</span>
                </div>
                <div className="mt-2 bg-muted rounded-full h-1.5">
                  <div className={`h-1.5 rounded-full ${getScoreBg(score)}`} style={{ width: `${score}%` }} />
                </div>
              </div>
            ))}
          </div>

          {/* Similarity + Predicted Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="font-semibold mb-4">Similarity Analysis</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      Winner Similarity
                    </span>
                    <span className="font-bold text-green-600">{formatPct(prediction.winner_similarity_pct)}</span>
                  </div>
                  <div className="bg-muted rounded-full h-2">
                    <div className="h-2 rounded-full bg-green-500" style={{ width: `${prediction.winner_similarity_pct}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="flex items-center gap-2">
                      <XCircle className="h-4 w-4 text-red-500" />
                      Loser Similarity
                    </span>
                    <span className="font-bold text-red-600">{formatPct(prediction.loser_similarity_pct)}</span>
                  </div>
                  <div className="bg-muted rounded-full h-2">
                    <div className="h-2 rounded-full bg-red-500" style={{ width: `${prediction.loser_similarity_pct}%` }} />
                  </div>
                </div>
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-orange-500" />
                      Fatigue Risk
                    </span>
                    <span className={`font-bold ${prediction.fatigue_risk_score > 60 ? "text-red-600" : "text-orange-500"}`}>
                      {prediction.fatigue_risk_score.toFixed(0)}/100
                    </span>
                  </div>
                  <div className="bg-muted rounded-full h-2">
                    <div className="h-2 rounded-full bg-orange-500" style={{ width: `${prediction.fatigue_risk_score}%` }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-5">
              <h3 className="font-semibold mb-4">Predicted Performance</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-muted-foreground">CTR</p>
                  <p className="text-xl font-bold">{formatCtr(prediction.predicted_ctr)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">CPA</p>
                  <p className="text-xl font-bold">{formatCurrency(prediction.predicted_cpa)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">ROAS</p>
                  <p className={`text-xl font-bold ${(prediction.predicted_roas || 0) >= 3 ? "text-green-600" : ""}`}>
                    {formatRoas(prediction.predicted_roas)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Lifespan</p>
                  <p className="text-xl font-bold">{formatDays(prediction.predicted_lifespan_days)}</p>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-xs text-muted-foreground">AI Analysis</p>
                <div className="mt-2 grid grid-cols-2 gap-1 text-xs">
                  <span className="text-muted-foreground">Narrative:</span>
                  <span className="font-medium">{formatNarrative(analysis.narrative_type)}</span>
                  <span className="text-muted-foreground">Hook:</span>
                  <span className="font-medium">{formatNarrative(analysis.hook_type)}</span>
                  <span className="text-muted-foreground">Creator:</span>
                  <span className="font-medium">{formatNarrative(analysis.creator_type)}</span>
                  <span className="text-muted-foreground">Funnel:</span>
                  <span className="font-medium">{formatNarrative(analysis.stage_of_funnel)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Opportunities & Risks */}
          {(prediction.opportunity_factors.length > 0 || prediction.risk_factors.length > 0) && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {prediction.opportunity_factors.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                  <h3 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" /> Why it will work
                  </h3>
                  <ul className="space-y-2">
                    {prediction.opportunity_factors.map((f, i) => (
                      <li key={i} className="text-sm text-green-800 flex items-start gap-2">
                        <ArrowRight className="h-3 w-3 mt-0.5 shrink-0" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {prediction.risk_factors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <h3 className="font-semibold text-red-900 mb-3 flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" /> Watch out for
                  </h3>
                  <ul className="space-y-2">
                    {prediction.risk_factors.map((f, i) => (
                      <li key={i} className="text-sm text-red-800 flex items-start gap-2">
                        <ArrowRight className="h-3 w-3 mt-0.5 shrink-0" />{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleReset}
            className="px-4 py-2 border border-border rounded-lg text-sm hover:bg-accent transition-colors"
          >
            Analyze another creative
          </button>
        </div>
      )}
    </div>
  );
}
